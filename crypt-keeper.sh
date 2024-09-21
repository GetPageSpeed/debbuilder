#!/usr/bin/env bash
set -exo pipefail
DOCKER_REGISTRY_USER=getpagespeed

# Declare a map for Ubuntu/Debian codename-based releases
declare -A DISTRO_DISTS=( [ubuntu]=ubuntu [debian]=debian )

function generate() {
    SOURCES=${SOURCES-/sources}
    OUTPUT=${OUTPUT-/output}
    WORKSPACE=${WORKSPACE-/workspace}
    DEB_BUILD_DIR=${DEB_BUILD_DIR-/debbuild}

    DISTRO=${1-ubuntu}
    RELEASE=${2-focal}

    ROOT=$(pwd)/${DISTRO}/${RELEASE}/
    ASSETS=${ROOT}/assets
    DOCKERFILE=${ROOT}/Dockerfile
    rm -rf "${ROOT}" && mkdir -p "${ROOT}"

    # Prepare files
    cp -R ./assets "${ROOT}"/.

    # Determine base image for the Dockerfile
    FROM_DISTRO="${DISTRO_DISTS[$DISTRO]}"
    FROM_RELEASE_TAG="${RELEASE}"

    # Generate Dockerfile
    cat > "${DOCKERFILE}" << EOF
FROM ${FROM_DISTRO}:${FROM_RELEASE_TAG}
LABEL maintainer="Danila Vershinin <info@getpagespeed.com>"

ENV WORKSPACE=${WORKSPACE} \\
    SOURCES=${SOURCES} \\
    OUTPUT=${OUTPUT} \\
    DEB_BUILD_DIR=${DEB_BUILD_DIR}

ADD ./assets/build /usr/bin/build
#ADD ./assets/deblint.config /etc/deblint/config
ADD ./assets/transient/* /tmp/

RUN sed -i 's@ports.ubuntu.com@mirror.yandex.ru@g' /etc/apt/sources.list && apt-get update

RUN DISTRO=${DISTRO} RELEASE=${RELEASE} /tmp/setup.sh

RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

VOLUME ["\${SOURCES}", "\${OUTPUT}"]

CMD ["build"]
EOF
}

function map-all() {
    while IFS=' ' read -r -a input; do
        $1 "${input[0]}" "${input[1]}"
    done < ./defaults
}

function docker-image-name() {
    DISTRO=${1}
    VERSION=${2}
    echo -n "${DOCKER_REGISTRY_USER}/debuilder:${DISTRO/\//-}-${VERSION}"
}

function docker-image-alt-name() {
    DISTRO=${1}
    VERSION=${2}
    DIST=${DISTRO_DISTS[$DISTRO]}
    echo -n "${DOCKER_REGISTRY_USER}/debuilder:${DIST}${VERSION}"
}

function build() {
    DISTRO=${1}
    VERSION=${2}
    MAIN_TAG="$(docker-image-name "${DISTRO}" "${VERSION}")"
    ALT_TAG="$(docker-image-alt-name "${DISTRO}" "${VERSION}")"
    # Ensure buildx is set up and ready for multi-architecture builds
    docker buildx create --use --name multiarch-builder --driver docker-container || true
    cd "${DISTRO}/${VERSION}" && docker buildx build --platform linux/amd64,linux/arm64 --push -t "${MAIN_TAG}" -t "${ALT_TAG}" .
    cd -
}

function push() {
    echo "Nothing to do, pushed in the build step"
}

function test() {
    # Test build
    DISTRO=${1}
    VERSION=${2}
    echo "Testing x86_64 build for ${DISTRO}-${VERSION}"
    docker run --rm --platform linux/amd64 -v "$(pwd)"/tests/hello:/sources "$(docker-image-name "${DISTRO}" "${VERSION}")" build
    echo "Done testing x86_64 build for ${DISTRO}-${VERSION}"
}

case "$1" in
    generate|build|push|test)
        if [ "$2" == "all" ]; then
            map-all "$1"
        else
            "$1" "$2" "$3"
        fi ;;
esac
