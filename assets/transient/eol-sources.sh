#!/bin/bash
# Point EOL base images at their archive mirrors so apt-get update still works.
# Runs in the Dockerfile BEFORE the first apt-get update (setup.sh is too late:
# the template's apt update would already have failed on a dead mirror).
#
# Only releases whose stock sources are actually dead belong here:
# - debian:10 (buster) images still point at deb.debian.org, which dropped
#   buster in 2024; the archive is on archive.debian.org (Release files are
#   final and unsigned-for-freshness, hence Check-Valid-Until off).
# - ubuntu:18.04 (bionic) still resolves on archive.ubuntu.com (ESM keeps it
#   there); if Canonical moves it to old-releases.ubuntu.com, add a case.
set -euo pipefail

. /etc/os-release

case "${ID}-${VERSION_CODENAME:-}" in
    debian-buster)
        printf '%s\n' \
            'deb http://archive.debian.org/debian buster main' \
            'deb http://archive.debian.org/debian buster-updates main' \
            'deb http://archive.debian.org/debian-security buster/updates main' \
            > /etc/apt/sources.list
        echo 'Acquire::Check-Valid-Until "false";' > /etc/apt/apt.conf.d/99-archive-valid-until
        ;;
    *)
        echo "eol-sources: nothing to do for ${ID} ${VERSION_CODENAME:-?}"
        ;;
esac
