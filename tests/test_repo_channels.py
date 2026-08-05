"""Regression tests for GetPageSpeed APT channel composition."""

from pathlib import Path
import subprocess
import unittest


BUILD_SCRIPT = Path(__file__).resolve().parents[1] / "assets" / "build"


def repo_suites(channel: str) -> list[str]:
    """Return suites emitted by the build script for a test channel."""
    result = subprocess.run(
        [
            "bash",
            "-c",
            'DEBBUILDER_HELPERS_ONLY=1 source "$1"; '
            'getpagespeed_repo_suites noble "$2"',
            "test-repo-channels",
            str(BUILD_SCRIPT),
            channel,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.splitlines()


class RepoChannelTest(unittest.TestCase):
    """Optional channels must retain stable as their dependency base."""

    def test_stable_channel_is_not_duplicated(self) -> None:
        self.assertEqual(repo_suites("main"), ["noble"])

    def test_mainline_channel_includes_stable_first(self) -> None:
        self.assertEqual(repo_suites("mainline"), ["noble", "noble-mainline"])


if __name__ == "__main__":
    unittest.main()
