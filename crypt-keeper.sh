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

ENV DEBIAN_FRONTEND=noninteractive

ADD ./assets/build /usr/bin/build
ADD ./assets/check-deps.sh /usr/bin/check-deps.sh
#ADD ./assets/deblint.config /etc/deblint/config
ADD ./assets/transient/* /tmp/

# Optimize apt settings for faster downloads
RUN echo 'Acquire::Retries "3";' > /etc/apt/apt.conf.d/80-retries && \\
    echo 'Acquire::http::Timeout "30";' >> /etc/apt/apt.conf.d/80-retries && \\
    echo 'Acquire::ftp::Timeout "30";' >> /etc/apt/apt.conf.d/80-retries && \\
    apt-get update

RUN apt-get install -y equivs

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
    echo -n "${DOCKER_REGISTRY_USER}/debbuilder:${DISTRO/\//-}-${VERSION}"
}

function docker-image-alt-name() {
    DISTRO=${1}
    VERSION=${2}
    DIST=${DISTRO_DISTS[$DISTRO]}
    echo -n "${DOCKER_REGISTRY_USER}/debbuilder:${DIST}${VERSION}"
}

function docker-image-dist-tag() {
    DISTRO=${1}
    VERSION=${2}

    # Create dist tags using version numbers (similar to RPM's %{?dist} system)
    # This matches patterns like ubuntu.24.04 seen in Plesk repositories
    case "${DISTRO}" in
        ubuntu)
            case "${VERSION}" in
                focal) echo -n "${DOCKER_REGISTRY_USER}/debbuilder:ubuntu20.04" ;;
                jammy) echo -n "${DOCKER_REGISTRY_USER}/debbuilder:ubuntu22.04" ;;
                noble) echo -n "${DOCKER_REGISTRY_USER}/debbuilder:ubuntu24.04" ;;
                kinetic) echo -n "${DOCKER_REGISTRY_USER}/debbuilder:ubuntu22.10" ;;
                *) echo -n "${DOCKER_REGISTRY_USER}/debbuilder:ubuntu${VERSION}" ;;
            esac
            ;;
        debian)
            case "${VERSION}" in
                bookworm) echo -n "${DOCKER_REGISTRY_USER}/debbuilder:debian12" ;;
                trixie) echo -n "${DOCKER_REGISTRY_USER}/debbuilder:debian13" ;;
                sid) echo -n "${DOCKER_REGISTRY_USER}/debbuilder:debian-sid" ;;
                *) echo -n "${DOCKER_REGISTRY_USER}/debbuilder:debian${VERSION}" ;;
            esac
            ;;
        *)
            echo -n "${DOCKER_REGISTRY_USER}/debbuilder:${DISTRO}${VERSION}"
            ;;
    esac
}

function build() {
    DISTRO=${1}
    VERSION=${2}
    MAIN_TAG="$(docker-image-name "${DISTRO}" "${VERSION}")"
    ALT_TAG="$(docker-image-alt-name "${DISTRO}" "${VERSION}")"
    DIST_TAG="$(docker-image-dist-tag "${DISTRO}" "${VERSION}")"

    # Ensure buildx is set up and ready for multi-architecture builds
    docker buildx create --use --name multiarch-builder --driver docker-container || true

    echo "Building multi-architecture image for ${DISTRO}-${VERSION}"
    echo "Tags: ${MAIN_TAG}, ${ALT_TAG}, ${DIST_TAG}"
    echo "Platforms: linux/amd64, linux/arm64"

    cd "${DISTRO}/${VERSION}" && docker buildx build \
        --platform linux/amd64,linux/arm64 \
        --push \
        -t "${MAIN_TAG}" \
        -t "${ALT_TAG}" \
        -t "${DIST_TAG}" \
        .
    cd -
}

function push() {
    echo "Nothing to do, pushed in the build step"
}

function test() {
    # Test build for both architectures
    DISTRO=${1}
    VERSION=${2}
    MAIN_TAG="$(docker-image-name "${DISTRO}" "${VERSION}")"

    echo "Testing x86_64 build for ${DISTRO}-${VERSION}"
    docker run --rm --platform linux/amd64 \
        -v "$(pwd)"/tests:/sources \
        -v "$(pwd)"/output:/output \
        "${MAIN_TAG}" build

    echo "Testing aarch64 build for ${DISTRO}-${VERSION}"
    docker run --rm --platform linux/arm64 \
        -v "$(pwd)"/tests:/sources \
        -v "$(pwd)"/output:/output \
        "${MAIN_TAG}" build

    echo "Done testing both architectures for ${DISTRO}-${VERSION}"
}

case "$1" in
    generate|build|push|test|docker-image-name|docker-image-alt-name|docker-image-dist-tag)
        if [ "$2" == "all" ]; then
            map-all "$1"
        else
            "$1" "$2" "$3"
        fi ;;
esac
