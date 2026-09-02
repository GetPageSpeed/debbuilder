#!/bin/bash
shopt -s extglob
set -euxo pipefail

install_required_packages() {
    local packages="$1"
    local max_attempts="${APT_INSTALL_ATTEMPTS:-3}"
    local retry_delay="${APT_RETRY_DELAY_SECONDS:-5}"
    local attempt=1

    while true; do
        # shellcheck disable=SC2086 # The package lists are intentionally word-split.
        if ${PKGR} -y install ${packages}; then
            return 0
        fi

        if (( attempt >= max_attempts )); then
            echo "Failed to install required packages after ${attempt} attempts: ${packages}" >&2
            return 1
        fi

        echo "Required package installation failed (attempt ${attempt}/${max_attempts}); refreshing indexes before retry..." >&2
        ${PKGR} update -y || true
        sleep "${retry_delay}"
        attempt=$((attempt + 1))
    done
}

# The GetPageSpeed DEB pool is subscription-gated per client IP, so a build
# runner is admitted by user agent instead, exactly like rpmbuilder's dnf plugin.
# The image workflow substitutes the DEBBUILDER_UA secret for the ten-X
# placeholder at build time; an unsubstituted or empty value keeps apt's
# default agent and the paid pool then answers 403 to build-dependency fetches.
configure_repo_user_agent() {
    local ua="$1"
    local conf="${2:-/etc/apt/apt.conf.d/90-getpagespeed-ua}"

    if [[ -z "${ua}" || "${ua}" == *XXXX* ]]; then
        echo "No builder user agent configured; GetPageSpeed pool fetches stay anonymous." >&2
        return 0
    fi

    printf 'Acquire::http::User-Agent "%s";\nAcquire::https::User-Agent "%s";\n' "${ua}" "${ua}" > "${conf}"
}

if [[ "${DEBBUILDER_SETUP_HELPERS_ONLY:-0}" == "1" ]]; then
    return 0
fi

# Set non-interactive frontend to avoid prompts during package installation
export DEBIAN_FRONTEND=noninteractive

# Pre-configure timezone to avoid tzdata interactive prompts
echo "tzdata tzdata/Areas select Etc" | debconf-set-selections
echo "tzdata tzdata/Zones/Etc select UTC" | debconf-set-selections

# Detect the distribution and release
if test -f /etc/os-release; then
   . /etc/os-release
elif test -f /usr/lib/os-release; then
   . /usr/lib/os-release
fi

# Detecting Ubuntu or Debian version using variable that were set by /etc/os-release without lsb_release
ID=${ID:-}
VERSION_CODENAME=${VERSION_CODENAME:-${VERSION_ID}}
echo "DISTRO: ${ID}, VERSION_CODENAME: ${VERSION_CODENAME}"

# Package manager for Debian/Ubuntu systems
PKGR="apt-get"
PACKAGES="build-essential debhelper dpkg-dev devscripts lintian fakeroot quilt"
PRE_PACKAGES="apt-transport-https ca-certificates curl gnupg bc"

# If any additional repositories need to be added (like GetPageSpeed or other custom repositories)
PRIMARY_REPO_PACKAGES="https://extras.getpagespeed.com/release-latest.deb"

# Enable necessary repositories for Ubuntu/Debian
# Ensure that multiverse or universe repos are enabled for specific package dependencies
# If Ubuntu
if [[ "${ID}" == "ubuntu" ]]; then
    ${PKGR} -y install software-properties-common || true
    add-apt-repository -y universe || true
    add-apt-repository -y multiverse || true
    # Enable backports on focal to satisfy newer build-deps like debhelper-compat (= 13)
    if [[ "${VERSION_CODENAME}" == "focal" ]]; then
        ARCH="$(dpkg --print-architecture 2>/dev/null || echo amd64)"
        UBUNTU_MIRROR="http://archive.ubuntu.com/ubuntu"
        # For non-amd64 architectures (e.g., arm64), use ports.ubuntu.com
        if [[ "${ARCH}" != "amd64" && "${ARCH}" != "i386" ]]; then
            UBUNTU_MIRROR="http://ports.ubuntu.com/ubuntu-ports"
        fi
        add-apt-repository -y "deb ${UBUNTU_MIRROR} focal-backports main universe multiverse"
    fi
fi

# Install primary packages (e.g., for GetPageSpeed repo)
#curl -L "${PRIMARY_REPO_PACKAGES}" -o /tmp/getpagespeed-release-latest.deb
#dpkg -i /tmp/getpagespeed-release-latest.deb || true
#rm -f /tmp/getpagespeed-release-latest.deb

# Update the package index (tolerate transient mirror sync issues)
n=0
until ${PKGR} update -y; do
  n=$((n+1))
  if [ $n -ge 3 ]; then
    echo "apt-get update failed after ${n} attempts; continuing with possibly stale indexes."
    break
  fi
  echo "apt-get update failed (attempt ${n}); retrying in 5s..."
  sleep 5
done
install_required_packages "${PRE_PACKAGES}"

# Substituted by .github/workflows/dockerbuild.yml from the DEBBUILDER_UA secret.
configure_repo_user_agent "XXXXXXXXXX"

# Install the core development and packaging tools
install_required_packages "${PACKAGES}"

# Create build directories
DEB_BUILD_DIR=/root/debbuild
SOURCES=${SOURCES:-/sources}
OUTPUT=${OUTPUT:-/output}
WORKSPACE=${WORKSPACE:-/workspace}

mkdir -p ${DEB_BUILD_DIR}/{BUILD,DEBS,SOURCES,SPECS,SRPMS}
ln -sf ${DEB_BUILD_DIR} /root/debbuild
mkdir -p ${SOURCES} ${WORKSPACE} ${OUTPUT}

# Setting up locales if necessary (to avoid issues during package builds)
locale-gen en_US.UTF-8 || true
export LANG=en_US.UTF-8
export LANGUAGE=en_US:en
export LC_ALL=en_US.UTF-8

# Clean up any unnecessary files to minimize Docker image size
${PKGR} clean
rm -rf /var/lib/apt/lists/*
