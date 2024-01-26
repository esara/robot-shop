import json
import pika
import os

from opentelemetry import trace
from opentelemetry.trace import StatusCode
from opentelemetry.instrumentation.pika import PikaInstrumentor
from opentelemetry.semconv.trace import SpanAttributes
from opentelemetry.sdk.trace import Span
from pika.spec import BasicProperties

class Publisher:
    HOST = os.getenv('AMQP_HOST', 'rabbitmq')
    VIRTUAL_HOST = '/'
    EXCHANGE='robot-shop'
    TYPE='direct'
    ROUTING_KEY = 'orders'

    def __init__(self, logger):
        self._logger = logger
        self._params = pika.connection.ConnectionParameters(
            host=self.HOST,
            virtual_host=self.VIRTUAL_HOST,
            credentials=pika.credentials.PlainCredentials('guest', 'guest'))
        self._conn = None
        self._channel = None

    def publish_hook(self, span: Span, body: bytes, properties: BasicProperties):
        span.set_attribute(SpanAttributes.MESSAGING_DESTINATION_NAME, self.ROUTING_KEY)

    def consume_hook(self, span: Span, body: bytes, properties: BasicProperties):
        span.set_attribute(SpanAttributes.MESSAGING_DESTINATION_NAME, self.ROUTING_KEY)

    def _connect(self):
        try:
            if not self._conn or self._conn.is_closed or self._channel is None or self._channel.is_closed:
                self._conn = pika.BlockingConnection(self._params)
                self._channel = self._conn.channel()
                self._channel.exchange_declare(exchange=self.EXCHANGE, exchange_type=self.TYPE, durable=True)
                self._logger.info('connected to broker')

                # Enable Pika instrumentation
                PikaInstrumentor.instrument_channel(self._channel, publish_hook=self.publish_hook, consume_hook=self.consume_hook)
        except Exception as e:
            # Log the exception
            self._logger.error(f'Failed to connect to RabbitMQ: {e}')

            # OpenTelemetry: Create a span and set status to ERROR
            with trace.get_tracer_provider().get_tracer(__name__).start_as_current_span("rabbitmq_connection_error") as span:
                span.set_status(StatusCode.ERROR, f"Failed to connect to RabbitMQ: {e}")

            # Re-raise the exception to notify the caller
            raise

    def _publish(self, msg, headers):
        self._channel.basic_publish(exchange=self.EXCHANGE,
                                    routing_key=self.ROUTING_KEY,
                                    properties=pika.BasicProperties(headers=headers),
                                    body=json.dumps(msg).encode())
        self._logger.info('message sent')

    #Publish msg, reconnecting if necessary.
    def publish(self, msg, headers):
        if self._channel is None or self._channel.is_closed or self._conn is None or self._conn.is_closed:
            self._connect()
        try:
            self._publish(msg, headers)
        except (pika.exceptions.ConnectionClosed, pika.exceptions.StreamLostError):
            self._logger.info('reconnecting to queue')
            self._connect()
            self._publish(msg, headers)

    def close(self):
        if self._conn and self._conn.is_open:
            self._logger.info('closing queue connection')
            self._conn.close()

