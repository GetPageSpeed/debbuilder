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


def channel_from_repo_id(repo_id: str) -> str:
    """Return the channel the build script derives from a CI repo identifier."""
    result = subprocess.run(
        [
            "bash",
            "-c",
            'DEBBUILDER_HELPERS_ONLY=1 source "$1"; '
            'getpagespeed_channel_from_repo_id "$2"',
            "test-repo-channels",
            str(BUILD_SCRIPT),
            repo_id,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


class RepoChannelTest(unittest.TestCase):
    """Optional channels must retain stable as their dependency base."""

    def test_stable_channel_is_not_duplicated(self) -> None:
        self.assertEqual(repo_suites("main"), ["noble"])

    def test_mainline_channel_includes_stable_first(self) -> None:
        self.assertEqual(repo_suites("mainline"), ["noble", "noble-mainline"])


class RepoIdChannelTest(unittest.TestCase):
    """--enable-repos identifiers must map to channels, never apt shortcuts.

    Regression for 2026-08-06: `add-apt-repository getpagespeed-extras-mainline`
    failed every nginx-deb-modules mainline job because the identifier is a
    GetPageSpeed channel name, not an apt repository shortcut.
    """

    def test_mainline_repo_id_maps_to_mainline_channel(self) -> None:
        self.assertEqual(channel_from_repo_id("getpagespeed-extras-mainline"), "mainline")

    def test_bare_repo_id_maps_to_main(self) -> None:
        self.assertEqual(channel_from_repo_id("getpagespeed-extras"), "main")

    def test_stable_repo_id_maps_to_main(self) -> None:
        self.assertEqual(channel_from_repo_id("getpagespeed-extras-stable"), "main")


if __name__ == "__main__":
    unittest.main()
