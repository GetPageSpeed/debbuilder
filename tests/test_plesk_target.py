import importlib.util
import json
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "assets" / "plesk-target.py"
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
        self.assertIn("PLESK_BASE_CONFIGURE_ARGS=", output)
        self.assertIn("--with-compat", output)


if __name__ == "__main__":
    unittest.main()
