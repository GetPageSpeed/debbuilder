import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def dist_tag(distro, codename, with_distmap=True):
    script = "" if with_distmap else "unset -f codename_to_numeric_tag 2>/dev/null;"
    out = subprocess.run(
        ["bash", "-c", f"set +x; {script} ./crypt-keeper.sh docker-image-dist-tag {distro} {codename} 2>/dev/null"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    )
    return out.stdout.strip().splitlines()[-1]


class DistTagTest(unittest.TestCase):
    def test_every_default_codename_gets_a_numeric_dist_tag(self):
        # An unmapped codename falls through to e.g. "ubunturesolute", which
        # never matches the ubuntu26.04 tag CI and rebuild tooling expect.
        for line in (ROOT / "defaults").read_text().split("\n"):
            if not line.strip():
                continue
            distro, codename = line.split()
            tag = dist_tag(distro, codename)
            self.assertRegex(tag, rf"^getpagespeed/debbuilder:{distro}[0-9][0-9.]*$", (distro, codename))

    def test_resolute_maps_to_ubuntu2604(self):
        self.assertEqual(dist_tag("ubuntu", "resolute"), "getpagespeed/debbuilder:ubuntu26.04")

    def test_image_matrix_lists_resolute(self):
        matrix = json.loads((ROOT / "distro_versions.json").read_text())["include"]
        self.assertIn({"os": "ubuntu", "version": "resolute"}, matrix)


if __name__ == "__main__":
    unittest.main()
