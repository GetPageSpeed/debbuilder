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


class RepoUserAgentTest(unittest.TestCase):
    """The paid DEB pool admits builders by user agent, never anonymously."""

    def _run(self, ua_literal: str) -> tuple[subprocess.CompletedProcess, Path]:
        import tempfile

        conf = Path(tempfile.mkdtemp()) / "90-getpagespeed-ua"
        result = run_helper(f"configure_repo_user_agent {ua_literal} '{conf}'")
        return result, conf

    def test_writes_apt_user_agent_for_http_and_https(self) -> None:
        result, conf = self._run("'builder-agent'")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            conf.read_text(),
            'Acquire::http::User-Agent "builder-agent";\n'
            'Acquire::https::User-Agent "builder-agent";\n',
        )

    def test_unsubstituted_placeholder_leaves_apt_default(self) -> None:
        result, conf = self._run("'XXXXXXXXXX'")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(conf.exists())
        self.assertIn("stay anonymous", result.stderr)

    def test_empty_secret_leaves_apt_default(self) -> None:
        result, conf = self._run("''")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(conf.exists())


if __name__ == "__main__":
    unittest.main()
