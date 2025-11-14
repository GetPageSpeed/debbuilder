#!/bin/bash
shopt -s extglob
set -euxo pipefail

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
        add-apt-repository -y "deb http://archive.ubuntu.com/ubuntu focal-backports main universe multiverse"
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
${PKGR} -y install ${PRE_PACKAGES} || true

# Install the core development and packaging tools
${PKGR} -y install ${PACKAGES} || true

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
