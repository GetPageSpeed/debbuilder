"""The packaging dir's debian/ must replace a tarball-shipped debian/.

Regression for the first lua-resty-deb publish (2026-10-21):
perusio/lua-resty-tarantool's release tarball ships its own debian/, which
used to win over the repo's generated packaging — producing a wrongly named
lua-resty-tarantool deb with a zstd control.tar that reprepro 5.5.1 rejects.
"""

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


class PackagingDebianPriorityTest(unittest.TestCase):
    def test_tarball_debian_is_replaced_by_packaging_debian(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source_dir = Path(temp_dir) / "pkg"
            build_root = Path(temp_dir) / "unpacked"
            (source_dir / "debian").mkdir(parents=True)
            (source_dir / "debian" / "control").write_text("Source: lua5.1-resty-tarantool\n")
            (build_root / "debian").mkdir(parents=True)
            (build_root / "debian" / "control").write_text("Source: lua-resty-tarantool\n")
            (build_root / "debian" / "rules").write_text("# upstream leftovers\n")

            result = run_helper(f'install_packaging_debian "{source_dir}" "{build_root}"')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                (build_root / "debian" / "control").read_text(),
                "Source: lua5.1-resty-tarantool\n",
            )
            self.assertFalse((build_root / "debian" / "rules").exists())

    def test_copies_when_tarball_has_no_debian(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source_dir = Path(temp_dir) / "pkg"
            build_root = Path(temp_dir) / "unpacked"
            (source_dir / "debian").mkdir(parents=True)
            (source_dir / "debian" / "control").write_text("Source: lua5.1-resty-http\n")
            build_root.mkdir()

            result = run_helper(f'install_packaging_debian "{source_dir}" "{build_root}"')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                (build_root / "debian" / "control").read_text(),
                "Source: lua5.1-resty-http\n",
            )


if __name__ == "__main__":
    unittest.main()
