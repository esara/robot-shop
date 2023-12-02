import json
import logging
import os
import time
import uuid
from datetime import datetime

import requests
from flask import Flask
from flask import jsonify
from flask import request
from rabbitmq import Publisher

def path(req):
    """ Use the first URI segment as the value for the 'path' label """
    return "/" + req.path[1:].split("/")[0] + "/<id>"

app = Flask(__name__)
app.logger.setLevel(logging.INFO)

CART = os.getenv('CART_HOST', 'cart')
USER = os.getenv('USER_HOST', 'user')
PAYMENT_GATEWAY = os.getenv('PAYMENT_GATEWAY')

failure_hour = int(os.getenv('FAILURE_HOUR', '20'))
failure_start_min = int(os.getenv('FAILURE_FROM_MINUTE', '30'))
failure_end_min = int(os.getenv('FAILURE_TILL_MINUTE', '60'))
print(f'Failure duration is from {failure_hour:02d}:{failure_start_min:02d} - {failure_hour:02d}:{failure_end_min:02d} UTC')

error_flag = False

@app.errorhandler(Exception)
def exception_handler(err):
    app.logger.exception(str(err))
    return str(err), 500

@app.route('/health', methods=['GET'])
def health():
    return 'OK'


@app.route('/pay/<id>', methods=['POST'])
def pay(id):
    app.logger.info('payment for {}'.format(id))
    cart = request.get_json()
    app.logger.info(cart)

    anonymous_user = True

    # check user exists
    try:
        req = requests.get('http://{user}:8080/check/{id}'.format(user=USER, id=id))
    except requests.exceptions.RequestException as err:
        app.logger.error(err)
        return str(err), 500
    if req.status_code == 200:
        anonymous_user = False

    # check that the cart is valid
    # this will blow up if the cart is not valid
    has_shipping = False
    if cart.get('items') is None:
        app.logger.warn('No items in cart')
        return 'No items in cart', 400
    for item in cart.get('items'):
        if item.get('sku') == 'SHIP':
            has_shipping = True

    if cart.get('total', 0) == 0 or has_shipping == False:
        app.logger.warn('cart not valid')
        return 'cart not valid', 400

    # dummy call to payment gateway, hope they don't object
    if PAYMENT_GATEWAY:
        try:
            req = requests.get(PAYMENT_GATEWAY)
        except requests.exceptions.RequestException as err:
            app.logger.error(err)
            return str(err), 500
        if req.status_code != 200:
            app.logger.error('{} returned {} - {}'.format(PAYMENT_GATEWAY, req.status_code, req.text))
            return 'payment error', req.status_code
        else:
            app.logger.info('{} returned 200'.format(PAYMENT_GATEWAY))

    # Generate order id
    orderid = str(uuid.uuid4())
    queueOrder({ 'orderid': orderid, 'user': id, 'cart': cart })

    # add to order history
    if not anonymous_user:
        try:
            req = requests.post('http://{user}:8080/order/{id}'.format(user=USER, id=id),
                    data=json.dumps({'orderid': orderid, 'cart': cart}),
                    headers={'Content-Type': 'application/json'})
            app.logger.info('order history returned {}'.format(req.status_code))
        except requests.exceptions.RequestException as err:
            app.logger.error(err)
            return str(err), 500

    # delete cart
    try:
        req = requests.delete('http://{cart}:8080/cart/{id}?error={error}'.format(cart=CART, id=id, error=error_flag))
    except requests.exceptions.RequestException as err:
        app.logger.error(err)
        return str(err), 500
    if req.status_code != 200:
        app.logger.error('cart delete returned {} - {}'.format(req.status_code, req.text))
        return 'order history update error', req.status_code
    else:
        app.logger.info('cart delete returned 200')

    return jsonify({ 'orderid': orderid })


def queueOrder(order):
    app.logger.info('queue order')

    # For screenshot demo requirements optionally add in a bit of delay
    delay = int(os.getenv('PAYMENT_DELAY_MS', 0))
    time.sleep(delay / 1000)

    headers = {}
    publisher.publish(order, headers)


def countItems(items):
    count = 0
    for item in items:
        if item.get('sku') != 'SHIP':
            count += item.get('qty')

    return count


# RabbitMQ
publisher = Publisher(app.logger)

if __name__ == "__main__":
    app.logger.info('Payment gateway {}'.format(PAYMENT_GATEWAY))
    port = int(os.getenv("SHOP_PAYMENT_PORT", "8080"))
    app.logger.info('Starting on port {}'.format(port))
    app.run(host='0.0.0.0', port=port)
