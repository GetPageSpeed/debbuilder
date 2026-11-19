"""Regression tests for GetPageSpeed APT channel composition."""

import os
from pathlib import Path
import subprocess
import tempfile
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


def repo_suites_early(
    channel: str, published: str, early_repos: str | None = "1"
) -> tuple[list[str], int, str]:
    """Run getpagespeed_repo_suites noble <channel> ubuntu with a fake curl.

    The fake curl exits 0 only for URLs containing one of the space-separated
    suite names in `published`, 22 otherwise, and logs every call. Returns
    (suites, exit status, text of the curl call log; empty if never called).
    """
    with tempfile.TemporaryDirectory(prefix="fake-curl-") as tmp:
        log = Path(tmp) / "curl.log"
        fake = Path(tmp) / "curl"
        fake.write_text(
            "#!/bin/bash\n"
            'echo "$*" >> "${FAKE_CURL_LOG}"\n'
            'for suite in ${FAKE_PUBLISHED}; do\n'
            '  case "${*: -1}" in */dists/"${suite}"/InRelease) exit 0;; esac\n'
            "done\n"
            "exit 22\n"
        )
        fake.chmod(0o755)
        env = dict(os.environ)
        env["PATH"] = f"{tmp}:{env['PATH']}"
        env["FAKE_CURL_LOG"] = str(log)
        env["FAKE_PUBLISHED"] = published
        env.pop("EARLY_REPOS", None)
        if early_repos is not None:
            env["EARLY_REPOS"] = early_repos
        result = subprocess.run(
            [
                "bash",
                "-c",
                'DEBBUILDER_HELPERS_ONLY=1 source "$1"; '
                'getpagespeed_repo_suites noble "$2" ubuntu',
                "test-repo-channels",
                str(BUILD_SCRIPT),
                channel,
            ],
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )
        calls = log.read_text() if log.exists() else ""
        return result.stdout.splitlines(), result.returncode, calls


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


class EarlySuiteTest(unittest.TestCase):
    """EARLY_REPOS=1 adds the early twin of each suite that is published."""

    def test_main_channel_adds_published_early_suite(self) -> None:
        suites, status, _ = repo_suites_early("main", "noble-early")
        self.assertEqual(status, 0)
        self.assertEqual(suites, ["noble", "noble-early"])

    def test_mainline_adds_both_early_twins_after_published_suites(self) -> None:
        suites, status, _ = repo_suites_early(
            "mainline", "noble-early noble-mainline-early"
        )
        self.assertEqual(status, 0)
        self.assertEqual(
            suites,
            ["noble", "noble-mainline", "noble-early", "noble-mainline-early"],
        )

    def test_unpublished_early_suite_is_skipped_without_failing(self) -> None:
        suites, status, calls = repo_suites_early("main", "")
        self.assertEqual(status, 0)
        self.assertEqual(suites, ["noble"])
        self.assertIn("/ubuntu/dists/noble-early/InRelease", calls)

    def test_early_repos_unset_never_probes(self) -> None:
        suites, status, calls = repo_suites_early(
            "main", "noble-early", early_repos=None
        )
        self.assertEqual(status, 0)
        self.assertEqual(suites, ["noble"])
        self.assertEqual(calls, "")


if __name__ == "__main__":
    unittest.main()


class BaseRepoAlwaysEnabledTest(unittest.TestCase):
    """The base GetPageSpeed repo is enabled unconditionally, not via --enable-repos.

    It is the dependency base for everything we build (openssl35-dev, module
    -dev libraries); before this it was only configured as a non-fatal side
    effect of the repo existence check.
    """

    def test_build_flow_sets_up_base_repo_unconditionally(self) -> None:
        text = BUILD_SCRIPT.read_text()
        idx_setup = text.find("setup_getpagespeed_repo main ||")
        idx_extra = text.find("\nenable_additional_repos\n")
        self.assertGreater(idx_setup, -1, "unconditional base repo setup missing")
        self.assertGreater(idx_extra, -1, "enable_additional_repos invocation missing")
        self.assertLess(
            idx_setup, idx_extra,
            "base repo setup must run before optional extra repos",
        )
