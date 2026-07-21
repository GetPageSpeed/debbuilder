#!/usr/bin/env python3
"""Select one Plesk build target from a committed plesk-builds.json manifest."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
from pathlib import Path


def os_release(path: Path = Path("/etc/os-release")) -> dict[str, str]:
    """Read the simple key/value fields needed from os-release."""
    values = {}
    for line in path.read_text().splitlines():
        if "=" not in line or line.startswith("#"):
            continue
        key, value = line.split("=", 1)
        values[key] = value.strip().strip('"')
    return values


def select_target(
    manifest: dict[str, object], family: str, version: str, architecture: str
) -> dict[str, object]:
    """Select and validate one target record."""
    normalized_version = version.removesuffix(".0") if family == "debian" else version
    key = f"{family}-{normalized_version}-{architecture}"
    targets = manifest.get("targets", {})
    if key not in targets:
        raise ValueError(f"Plesk target {key} is not present in the manifest")
    target = targets[key]
    required = (
        "nginx_version",
        "nginx_source_url",
        "sw_nginx_version",
        "fingerprint",
        "configure_args",
        "packages",
    )
    missing = [field for field in required if not target.get(field)]
    if missing:
        raise ValueError(f"Plesk target {key} is missing: {', '.join(missing)}")
    if "--with-compat" not in target["configure_args"]:
        raise ValueError(f"Plesk target {key} does not contain --with-compat")
    return target


def shell_assignments(target: dict[str, object]) -> str:
    """Render target values as safely quoted shell assignments."""
    packages = target["packages"]
    values = {
        "PLESK_NGINX_VERSION": target["nginx_version"],
        "PLESK_NGINX_SOURCE_URL": target["nginx_source_url"],
        "PLESK_SW_NGINX_PACKAGE_VERSION": target["sw_nginx_version"],
        "PLESK_BUILD_FINGERPRINT": target["fingerprint"],
        "PLESK_BASE_CONFIGURE_ARGS": shlex.join(target["configure_args"]),
        "PLESK_SW_NGINX_URL": packages["sw-nginx"]["url"],
        "PLESK_MOD_SECURITY_URL": packages["mod-security-v3"]["url"],
    }
    return "\n".join(f"{key}={shlex.quote(str(value))}" for key, value in values.items())


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--family")
    parser.add_argument("--version")
    parser.add_argument("--architecture")
    parser.add_argument("--shell", action="store_true")
    args = parser.parse_args()
    release = os_release() if not args.family or not args.version else {}
    family = args.family or release.get("ID", "")
    version = args.version or release.get("VERSION_ID", "")
    architecture = args.architecture or subprocess.check_output(
        ["dpkg", "--print-architecture"], text=True
    ).strip()
    manifest = json.loads(args.manifest.read_text())
    target = select_target(manifest, family, version, architecture)
    if args.shell:
        print(shell_assignments(target))
    else:
        print(json.dumps(target, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
