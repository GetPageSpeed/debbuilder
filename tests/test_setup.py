"""Regression tests for debbuilder image setup helpers."""

from __future__ import annotations

from pathlib import Path
import subprocess
import unittest


SETUP_SCRIPT = Path(__file__).resolve().parents[1] / "assets" / "transient" / "setup.sh"


def run_helper(command: str) -> subprocess.CompletedProcess:
    """Source setup helpers and run a shell command."""
    return subprocess.run(
        [
            "bash",
            "-c",
            f'DEBBUILDER_SETUP_HELPERS_ONLY=1 source "{SETUP_SCRIPT}"; {command}',
        ],
        capture_output=True,
        text=True,
    )


class RequiredPackageInstallTest(unittest.TestCase):
    """Required tools must never be omitted from a published image."""

    def test_retries_a_transient_install_failure(self) -> None:
        result = run_helper(
            "attempts=0; "
            "fake_apt() { "
            "if [[ $1 == update ]]; then return 0; fi; "
            "attempts=$((attempts + 1)); [[ $attempts -ge 2 ]]; "
            "}; "
            "PKGR=fake_apt APT_INSTALL_ATTEMPTS=3 APT_RETRY_DELAY_SECONDS=0 "
            "install_required_packages 'debuild devscripts'; "
            "printf '%s' \"$attempts\""
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "2")

    def test_fails_after_retry_budget_is_exhausted(self) -> None:
        result = run_helper(
            "fake_apt() { [[ $1 == update ]]; }; "
            "PKGR=fake_apt APT_INSTALL_ATTEMPTS=2 APT_RETRY_DELAY_SECONDS=0 "
            "install_required_packages 'debuild devscripts'"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Failed to install required packages after 2 attempts", result.stderr)


if __name__ == "__main__":
    unittest.main()
