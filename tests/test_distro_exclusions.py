"""Regression tests for explicit per-distro package exclusions."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


BUILD_SCRIPT = Path(__file__).resolve().parents[1] / "assets" / "build"


def run_helper(command: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    test_env = os.environ.copy()
    test_env["DEBBUILDER_HELPERS_ONLY"] = "1"
    if env:
        test_env.update(env)
    return subprocess.run(
        ["bash", "-c", f'source "$1"; {command}', "test-helper", str(BUILD_SCRIPT)],
        capture_output=True,
        env=test_env,
        text=True,
    )


class DistroExclusionsTest(unittest.TestCase):
    def test_dist_id_normalizes_version_punctuation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            os_release = Path(temp_dir) / "os-release"
            os_release.write_text('ID=ubuntu\nVERSION_ID="20.04"\n')
            result = run_helper(
                "debbuilder_dist_id",
                {"DEBBUILDER_OS_RELEASE": str(os_release)},
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), "ubuntu2004")

    def test_exact_and_glob_exclusions_match(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir)
            debian = source / "debian"
            debian.mkdir()
            (debian / "debbuilder-exclude-dists").write_text(
                "# Known unavailable dependencies\nubuntu20*\ndebian13\n"
            )
            exact = run_helper(f'package_excluded_for_dist "{source}" debian13')
            glob = run_helper(f'package_excluded_for_dist "{source}" ubuntu2004')
            miss = run_helper(f'package_excluded_for_dist "{source}" ubuntu2204')
            self.assertEqual(exact.returncode, 0, exact.stderr)
            self.assertEqual(glob.returncode, 0, glob.stderr)
            self.assertNotEqual(miss.returncode, 0)

    def test_any_plesk_failure_is_fatal(self) -> None:
        fatal = run_helper("PLESK_BUILD=true plesk_failure_is_fatal 1")
        clean = run_helper("PLESK_BUILD=true plesk_failure_is_fatal 0")
        ordinary = run_helper("PLESK_BUILD=false plesk_failure_is_fatal 1")
        self.assertEqual(fatal.returncode, 0, fatal.stderr)
        self.assertNotEqual(clean.returncode, 0)
        self.assertNotEqual(ordinary.returncode, 0)


if __name__ == "__main__":
    unittest.main()
