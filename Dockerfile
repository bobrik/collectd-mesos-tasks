FROM alpine:3.1

RUN apk --update add collectd collectd-python py-pip && \
    pip install envtpl

COPY ./collectd.conf.tpl /etc/collectd/collectd.conf.tpl
COPY ./mesos-tasks.py /usr/share/collectd/plugins/mesos/

COPY ./run.sh /run.sh

ENTRYPOINT ["/run.sh"]
