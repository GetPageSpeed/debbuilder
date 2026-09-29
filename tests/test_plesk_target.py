import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "assets" / "plesk-target.py"
SPEC = importlib.util.spec_from_file_location("plesk_target", MODULE_PATH)
plesk_target = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(plesk_target)


class PleskTargetTest(unittest.TestCase):
    def setUp(self):
        self.target = {
            "nginx_version": "1.30.3",
            "nginx_source_url": "https://nginx.org/download/nginx-1.30.3.tar.gz",
            "sw_nginx_version": "1.30.3-v.debian.13+p18.0.79.2+t260708.1058",
            "fingerprint": "p18.0.79.2.t260708.1058",
            "configure_args": ["--prefix=/usr/share", "--with-compat"],
            "packages": {
                "sw-nginx": {"url": "https://example.test/sw-nginx.deb"},
                "mod-security-v3": {"url": "https://example.test/mod-security.deb"},
            },
        }
        self.manifest = {"targets": {"debian-13-amd64": self.target}}

    def test_selects_debian_target_with_dot_zero_version(self):
        selected = plesk_target.select_target(
            self.manifest, "debian", "13.0", "amd64"
        )
        self.assertEqual(selected["nginx_version"], "1.30.3")

    def test_rejects_unsupported_architecture(self):
        with self.assertRaisesRegex(ValueError, "not present"):
            plesk_target.select_target(self.manifest, "debian", "13", "arm64")

    def test_shell_output_contains_quoted_exact_version(self):
        output = plesk_target.shell_assignments(self.target)
        self.assertIn("PLESK_SW_NGINX_PACKAGE_VERSION=", output)
        self.assertIn("PLESK_NGINX_SOURCE_URL=", output)
        self.assertIn("PLESK_NGINX_ABI_VERSION=1.30.3", output)
        self.assertIn("PLESK_BASE_CONFIGURE_ARGS=", output)
        self.assertIn("--with-compat", output)

    def test_respin_package_uses_exact_nginx_source_abi(self):
        self.target["nginx_version"] = "1.30.4.1"
        self.target["nginx_source_url"] = (
            "https://nginx.org/download/nginx-1.30.4.tar.gz"
        )

        output = plesk_target.shell_assignments(self.target)

        self.assertIn("PLESK_NGINX_ABI_VERSION=1.30.4", output)

    def test_rejects_source_url_without_semantic_nginx_version(self):
        with self.assertRaisesRegex(ValueError, "Cannot derive NGINX ABI"):
            plesk_target.nginx_abi_version("https://example.test/nginx-current.tar.gz")

    def test_build_stamps_exact_join_placeholders_in_all_package_metadata(self):
        build = (ROOT / "assets" / "build").read_text()

        self.assertIn('"PLESK_NGINX_ABI_VERSION": abi_version', build)
        self.assertIn('"PLESK_BUILD_FINGERPRINT": fingerprint', build)
        self.assertIn(
            'for relative in ("debian/control", "debian/changelog", "debian/rules")',
            build,
        )

    def test_build_selects_package_specific_historical_manifest(self):
        build = (ROOT / "assets" / "build").read_text()

        self.assertIn('-f "plesk-builds.json"', build)
        self.assertIn('select_plesk_manifest "plesk-builds.json"', build)


class SelectPleskManifestTest(unittest.TestCase):
    """select_plesk_manifest must surface plesk-target failures to callers.

    Mid-rollout, per-fingerprint retained-join manifests cover only a subset
    of suites (2026-09-29 straddle). `eval "$(plesk-target ...)"` used to
    discard the exit code, so a missing target evaluated nothing and
    "succeeded" with empty values; the retained-join call site now skips on
    failure instead of failing the lane.
    """

    def run_select(self, plesk_target_stub: str, tmp: Path):
        import os
        import subprocess

        stub_dir = tmp / "stubs"
        stub_dir.mkdir()
        stub = stub_dir / "plesk-target"
        stub.write_text("#!/bin/bash\n" + plesk_target_stub + "\n")
        stub.chmod(0o755)
        env = os.environ.copy()
        env["DEBBUILDER_HELPERS_ONLY"] = "1"
        env["PATH"] = f"{stub_dir}:{env['PATH']}"
        command = (
            'source "$1"; '
            "if select_plesk_manifest manifest.json; then "
            '  echo "SELECTED=${PLESK_SW_NGINX_PACKAGE_VERSION}"; '
            "else echo MISSING; fi"
        )
        return subprocess.run(
            ["bash", "-c", command, "test-helper", str(ROOT / "assets" / "build")],
            capture_output=True,
            env=env,
            text=True,
        )

    def test_missing_target_is_a_detectable_failure_not_empty_success(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_select(
                'echo "Plesk target absent" >&2; exit 1', Path(tmp)
            )
        self.assertEqual(result.stdout.strip(), "MISSING", result.stderr)

    def test_present_target_still_selects_and_exports(self):
        import tempfile

        assignments = (
            "echo PLESK_NGINX_VERSION=1.30.5\n"
            "echo PLESK_NGINX_SOURCE_URL=https://nginx.org/download/nginx-1.30.5.tar.gz\n"
            "echo PLESK_NGINX_ABI_VERSION=1.30.5\n"
            "echo PLESK_SW_NGINX_PACKAGE_VERSION=1.30.5.1\n"
            "echo PLESK_BUILD_FINGERPRINT=p18.0.81.2.t260925.2015\n"
            "echo PLESK_BASE_CONFIGURE_ARGS=--with-compat\n"
            "echo PLESK_SW_NGINX_URL=https://example.test/sw-nginx.deb\n"
            "echo PLESK_MOD_SECURITY_URL=https://example.test/modsec.deb"
        )
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_select(assignments, Path(tmp))
        self.assertEqual(result.stdout.strip(), "SELECTED=1.30.5.1", result.stderr)

    def test_retained_join_call_site_skips_on_selection_failure(self):
        build = (ROOT / "assets" / "build").read_text()

        self.assertIn('if ! select_plesk_manifest "plesk-builds.json"; then', build)
        self.assertIn("no target in its retained Plesk join manifest", build)


if __name__ == "__main__":
    unittest.main()
