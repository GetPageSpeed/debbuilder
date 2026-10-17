"""The already-published check must not flake under `set -o pipefail`.

`apt-cache show pkg=ver | grep -q .` lets grep exit on the first byte, so
apt-cache dies of SIGPIPE mid-stanza and pipefail reports the published
version as missing. On 2026-10-17 that rebuilt about half of every cohort
lane and filled the repo's _conflict quarantine with same-NVR rejects.
"""

from __future__ import annotations

import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest


BUILD_SCRIPT = Path(__file__).resolve().parents[1] / "assets" / "build"

# A stanza far larger than a pipe buffer, written in small chunks: the reader
# leaves after the first byte, so any later write hits SIGPIPE.
FAKE_APT_CACHE = """#!/bin/bash
if [[ "$1" == "show" && "$2" == "nginx-module-lua=1.0-1" ]]; then
    for i in $(seq 1 4000); do printf 'Description-line-%05d: padding padding padding\\n' "$i"; done
    exit 0
fi
echo "E: Version '${2#*=}' for '${2%%=*}' was not found" >&2
exit 100
"""


class AptHasExactVersionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        fake = Path(self.tmp.name) / "apt-cache"
        fake.write_text(FAKE_APT_CACHE)
        fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
        self.env = os.environ.copy()
        self.env["DEBBUILDER_HELPERS_ONLY"] = "1"
        self.env["PATH"] = f"{self.tmp.name}:{self.env['PATH']}"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_bash(self, command: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["bash", "-c", f'source "$1"; set +x; {command}', "t", str(BUILD_SCRIPT)],
            capture_output=True,
            env=self.env,
            text=True,
        )

    def test_published_version_is_found_every_time(self) -> None:
        result = self.run_bash(
            "ok=0; for i in $(seq 1 25); do "
            "apt_has_exact_version nginx-module-lua 1.0-1 && ok=$((ok+1)); done; echo $ok"
        )
        self.assertEqual(result.stdout.strip().splitlines()[-1], "25", result.stderr[-500:])

    def test_missing_version_is_reported_missing(self) -> None:
        result = self.run_bash(
            "if apt_has_exact_version nginx-module-lua 2.0-1; then echo found; else echo missing; fi"
        )
        self.assertEqual(result.stdout.strip().splitlines()[-1], "missing")

    def test_old_grep_q_pipeline_really_flakes_with_this_fake(self) -> None:
        # Guards the test itself: the fake must reproduce the SIGPIPE false
        # negative, or the 25/25 assertion above proves nothing.
        result = self.run_bash(
            "bad=0; for i in $(seq 1 25); do "
            "apt-cache show nginx-module-lua=1.0-1 2>/dev/null | grep -q . || bad=$((bad+1)); done; echo $bad"
        )
        self.assertGreater(int(result.stdout.strip().splitlines()[-1]), 0)

    def test_check_uses_the_helper_not_a_grep_q_pipeline(self) -> None:
        source = BUILD_SCRIPT.read_text()
        self.assertIn('apt_has_exact_version "${package_name}" "${package_version}"', source)
        code = "\n".join(l for l in source.splitlines() if not l.lstrip().startswith("#"))
        self.assertNotRegex(code, r"apt-cache show [^\n]*\| *grep -q")


if __name__ == "__main__":
    unittest.main()
