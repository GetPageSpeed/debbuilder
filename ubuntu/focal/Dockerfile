FROM ubuntu:focal
LABEL maintainer="Danila Vershinin <info@getpagespeed.com>"

ENV WORKSPACE=/workspace \
    SOURCES=/sources \
    OUTPUT=/output \
    DEB_BUILD_DIR=/debbuild

ADD ./assets/build /usr/bin/build
#ADD ./assets/deblint.config /etc/deblint/config
ADD ./assets/transient/* /tmp/

RUN sed -i 's@ports.ubuntu.com@mirror.yandex.ru@g' /etc/apt/sources.list && sed -i 's@ports.ubuntu.com@mirror.yandex.ru@g' /etc/apt/sources.list.d/* && apt-get update
# RUN sed -i 's@ports.ubuntu.com@id.ports.ubuntu.com@g' /etc/apt/sources.list && sed -i 's@ports.ubuntu.com@id.ports.ubuntu.com@g' /etc/apt/sources.list.d/* && apt-get update


RUN DISTRO=ubuntu RELEASE=focal /tmp/setup.sh

RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

VOLUME ["${SOURCES}", "${OUTPUT}"]

CMD ["build"]
