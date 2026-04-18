FROM mysql:8

COPY ./local_setting/local_mysql/init.sql /docker-entrypoint-initdb.d/
COPY ./local_setting/local_mysql/conf.d /etc/mysql/conf.d
RUN chmod 644 /etc/mysql/conf.d/my.cnf
