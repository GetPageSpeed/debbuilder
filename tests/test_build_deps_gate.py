"""Per-package Build-Depends round-trip is skipped once deps are installed.

A cohort lane builds ~110 nginx modules in one container. Every package used
to run `apt-get update`, check-deps.sh and mk-build-deps even when an earlier
module had already installed the identical Build-Depends; with lanes running
5000-6500s (2026-10-15) and the CircleCI Free 1h job cap, that repeated work
matters. These tests pin the two gates that now skip it.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


BUILD_SCRIPT = Path(__file__).resolve().parents[1] / "assets" / "build"


def run_helper(command: str, cwd: str, env: dict[str, str]) -> subprocess.CompletedProcess:
    test_env = os.environ.copy()
    test_env["DEBBUILDER_HELPERS_ONLY"] = "1"
    test_env.update(env)
    return subprocess.run(
        ["bash", "-c", f'source "$1"; {command}', "test-helper", str(BUILD_SCRIPT)],
        capture_output=True,
        cwd=cwd,
        env=test_env,
        text=True,
    )


class AptListsFreshnessTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.stamp = os.path.join(self.tmp.name, "stamp")
        self.env = {"APT_LISTS_STAMP": self.stamp}

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def fresh(self, extra: dict[str, str] | None = None) -> str:
        env = dict(self.env, **(extra or {}))
        result = run_helper("apt_lists_fresh && echo FRESH || echo STALE", self.tmp.name, env)
        return result.stdout.strip()

    def test_no_stamp_means_stale(self) -> None:
        self.assertEqual(self.fresh(), "STALE")

    def test_marked_lists_are_fresh(self) -> None:
        run_helper("mark_apt_lists_fresh", self.tmp.name, self.env)
        self.assertEqual(self.fresh(), "FRESH")

    def test_old_stamp_is_stale(self) -> None:
        run_helper("mark_apt_lists_fresh", self.tmp.name, self.env)
        old = os.path.getmtime(self.stamp) - 3600
        os.utime(self.stamp, (old, old))
        self.assertEqual(self.fresh(), "STALE")

    def test_max_age_is_tunable(self) -> None:
        run_helper("mark_apt_lists_fresh", self.tmp.name, self.env)
        old = os.path.getmtime(self.stamp) - 120
        os.utime(self.stamp, (old, old))
        self.assertEqual(self.fresh({"APT_LISTS_MAX_AGE": "60"}), "STALE")
        self.assertEqual(self.fresh({"APT_LISTS_MAX_AGE": "600"}), "FRESH")


class BuildDepsSatisfiedTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.bin = os.path.join(self.tmp.name, "bin")
        os.mkdir(self.bin)
        self.src = os.path.join(self.tmp.name, "src")
        os.makedirs(os.path.join(self.src, "debian"))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def stub_checkbuilddeps(self, exit_code: int) -> None:
        path = os.path.join(self.bin, "dpkg-checkbuilddeps")
        with open(path, "w") as handle:
            handle.write(f"#!/bin/sh\necho called >> \"$0.log\"\nexit {exit_code}\n")
        os.chmod(path, 0o755)

    def satisfied(self) -> str:
        env = {"PATH": f"{self.bin}:{os.environ['PATH']}"}
        result = run_helper("build_deps_satisfied && echo YES || echo NO", self.src, env)
        return result.stdout.strip()

    def test_missing_control_is_never_satisfied(self) -> None:
        self.stub_checkbuilddeps(0)
        self.assertEqual(self.satisfied(), "NO")
        self.assertFalse(os.path.exists(os.path.join(self.bin, "dpkg-checkbuilddeps.log")))

    def test_checkbuilddeps_pass_skips_install(self) -> None:
        Path(self.src, "debian", "control").write_text("Source: x\n")
        self.stub_checkbuilddeps(0)
        self.assertEqual(self.satisfied(), "YES")

    def test_unmet_deps_force_install(self) -> None:
        # dpkg-checkbuilddeps exits 1 on unmet (incl. versioned) Build-Depends.
        Path(self.src, "debian", "control").write_text("Source: x\n")
        self.stub_checkbuilddeps(1)
        self.assertEqual(self.satisfied(), "NO")


class BuildFlowWiringTest(unittest.TestCase):
    def test_install_round_trip_is_gated(self) -> None:
        text = BUILD_SCRIPT.read_text()
        gate = text.index("    if build_deps_satisfied; then")
        self.assertLess(gate, text.index("mk-build-deps -t"))
        self.assertLess(gate, text.index("            /usr/bin/check-deps.sh"))
        self.assertLess(gate, text.index("        elif ! apt-get update; then"))
        self.assertLess(text.index("mk-build-deps -t"), text.index("    debuild -us -uc -b"))


if __name__ == "__main__":
    unittest.main()
