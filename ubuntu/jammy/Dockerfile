FROM ubuntu:jammy
LABEL maintainer="Danila Vershinin <info@getpagespeed.com>"

ENV WORKSPACE=/workspace \
    SOURCES=/sources \
    OUTPUT=/output \
    DEB_BUILD_DIR=/debbuild

ADD ./assets/build /usr/bin/build
ADD ./assets/check-deps.sh /usr/bin/check-deps.sh
#ADD ./assets/deblint.config /etc/deblint/config
ADD ./assets/transient/* /tmp/

# Optimize apt settings for faster downloads
RUN echo 'Acquire::Retries "3";' > /etc/apt/apt.conf.d/80-retries && \
    echo 'Acquire::http::Timeout "30";' >> /etc/apt/apt.conf.d/80-retries && \
    echo 'Acquire::ftp::Timeout "30";' >> /etc/apt/apt.conf.d/80-retries && \
    apt-get update

RUN apt-get install -y equivs
RUN chmod +x /usr/bin/build /usr/bin/check-deps.sh

RUN DISTRO=ubuntu RELEASE=jammy /tmp/setup.sh

RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

VOLUME ["${SOURCES}", "${OUTPUT}"]

CMD ["build"]
