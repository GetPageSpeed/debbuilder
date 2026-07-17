import subprocess
import tempfile
import unittest
from pathlib import Path


BUILD_SCRIPT = Path(__file__).resolve().parents[1] / "assets/build"


class VersionYamlTest(unittest.TestCase):
    def test_tag_no_prefix_can_override_debian_version(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            version_path = Path(temp_dir) / "version.yml"
            version_path.write_text(
                'repo: "dvershinin/ngx_pagespeed"\n'
                'tag: "v2.1.0-beta10"\n'
                'tag_no_prefix: "2.1.0~beta10" # Debian prerelease order\n'
            )
            command = (
                f'DEBBUILDER_HELPERS_ONLY=1 source "{BUILD_SCRIPT}"; '
                f'read_simple_yaml_value "{version_path}" tag_no_prefix'
            )
            result = subprocess.run(
                ["bash", "-c", command],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.stdout.strip(), "2.1.0~beta10")


if __name__ == "__main__":
    unittest.main()
