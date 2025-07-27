FROM --platform=linux/amd64 ubuntu:jammy
LABEL maintainer="Danila Vershinin <info@getpagespeed.com>"

ENV WORKSPACE=/workspace \
    SOURCES=/sources \
    OUTPUT=/output \
    DEB_BUILD_DIR=/debbuild

ADD ./assets/build /usr/bin/build
#ADD ./assets/deblint.config /etc/deblint/config
ADD ./assets/transient/* /tmp/

# Optimize apt settings for faster downloads
RUN echo 'Acquire::Retries "3";' > /etc/apt/apt.conf.d/80-retries && \
    echo 'Acquire::http::Timeout "30";' >> /etc/apt/apt.conf.d/80-retries && \
    echo 'Acquire::ftp::Timeout "30";' >> /etc/apt/apt.conf.d/80-retries

# Fix repository URLs for different architectures before first update
RUN if [[ $(uname -m) == "aarch64" || $(uname -m) == "arm64" ]]; then \
        sed -i 's|ports.ubuntu.com|archive.ubuntu.com|g' /etc/apt/sources.list && \
        sed -i 's|ubuntu-ports|ubuntu|g' /etc/apt/sources.list; \
    fi

# Update GPG keys to fix signature issues
RUN apt-get update --allow-releaseinfo-change || true

RUN DISTRO=ubuntu RELEASE=jammy /tmp/setup.sh

RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

VOLUME ["${SOURCES}", "${OUTPUT}"]

CMD ["build"]
