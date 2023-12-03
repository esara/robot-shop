FROM php:8.4-apache

RUN apt-get update && apt-get install -yqq unzip libzip-dev \
    && docker-php-ext-install pdo_mysql opcache zip

# Datadog installation: APM  + Profiling (Beta)
RUN curl -sLO https://github.com/DataDog/dd-trace-php/releases/latest/download/datadog-setup.php
RUN php datadog-setup.php --php-bin=all --enable-profiling

# relax permissions on status
COPY status.conf /etc/apache2/mods-available/status.conf
# Enable Apache mod_rewrite and status
RUN a2enmod rewrite && a2enmod status

WORKDIR /var/www/html

COPY html/ /var/www/html

COPY --from=composer /usr/bin/composer /usr/bin/composer
RUN composer install

# This is important. Symfony needs write permissions and we
# dont know the context in which the container will run, i.e.
# which user will be forced from the outside so better play
# safe for this simple demo.
RUN rm -Rf /var/www/var/*
RUN chown -R www-data /var/www
RUN chmod -R 777 /var/www
