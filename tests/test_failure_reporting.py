"""Regression tests for cohort failure visibility.

The DEB cohort deliberately tolerates a share of broken packages. Until
2026-08-09 that tolerance was both silent and, because of a string-vs-numeric
comparison bug, effectively unlimited -- so a module could fail on every run
forever while the build stayed green and its .deb was never published. These
tests pin the two fixes.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET


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


class FailureToleranceTest(unittest.TestCase):
    def test_single_failure_in_a_cohort_is_under_tolerance(self) -> None:
        result = run_helper('failure_tolerance_exceeded 1 130 0.1 && echo YES || echo NO')
        self.assertEqual(result.stdout.strip(), "NO", result.stderr)

    def test_tolerance_is_exceeded_well_before_total_failure(self) -> None:
        # THE BUG: `[[ $(bc <<< "scale=2; 1/2") > 0.1 ]]` compared ".50" against
        # "0.1" as strings. "." sorts below "0", so half the cohort failing read
        # as within a 10% tolerance. Only "1.00" ever tripped it.
        for fail, total in ((2, 13), (1, 2), (7, 10)):
            with self.subTest(fail=fail, total=total):
                result = run_helper(
                    f"failure_tolerance_exceeded {fail} {total} 0.1 && echo YES || echo NO"
                )
                self.assertEqual(result.stdout.strip(), "YES", result.stderr)

    def test_the_old_string_comparison_would_have_passed_these(self) -> None:
        # Control: proves the cases above are exactly the ones the old form got
        # wrong, so this suite would have caught the original bug.
        for fail, total in ((2, 13), (1, 2), (7, 10)):
            with self.subTest(fail=fail, total=total):
                old = subprocess.run(
                    [
                        "bash",
                        "-c",
                        f'[[ $(echo "scale=2; {fail} / {total}" | bc) > 0.1 ]] '
                        "&& echo YES || echo NO",
                    ],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(old.stdout.strip(), "NO")

    def test_boundary_is_strictly_greater_than(self) -> None:
        result = run_helper("failure_tolerance_exceeded 1 10 0.1 && echo YES || echo NO")
        self.assertEqual(result.stdout.strip(), "NO", result.stderr)

    def test_zero_packages_never_divides_by_zero(self) -> None:
        result = run_helper("failure_tolerance_exceeded 0 0 0.1 && echo YES || echo NO")
        self.assertEqual(result.stdout.strip(), "NO", result.stderr)

    def test_tolerance_is_configurable_from_the_environment(self) -> None:
        script = BUILD_SCRIPT.read_text()
        self.assertIn("failure_tolerance=${FAILURE_TOLERANCE:-0.1}", script)


class JUnitReportTest(unittest.TestCase):
    def test_report_is_valid_xml_with_per_package_testcases(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir) / "nested" / "build-results.xml"
            result = run_helper(
                f'junit_write_report "{dest}" '
                '\'  <testcase classname="deb-build" name="nginx-module-ok" time="3"/>\' '
                '\'  <testcase classname="deb-build" name="nginx-module-bad" time="1">'
                '<failure message="Build failed">boom</failure></testcase>\''
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            suite = ET.parse(dest).getroot()
            self.assertEqual(suite.tag, "testsuite")
            self.assertEqual(suite.get("tests"), "2")
            self.assertEqual(suite.get("failures"), "1")

            names = [case.get("name") for case in suite.findall("testcase")]
            self.assertEqual(names, ["nginx-module-ok", "nginx-module-bad"])

            failed = suite.find('testcase[@name="nginx-module-bad"]/failure')
            self.assertIsNotNone(failed)
            self.assertEqual(failed.text, "boom")

    def test_report_is_valid_xml_when_nothing_failed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir) / "build-results.xml"
            run_helper(
                f'junit_write_report "{dest}" '
                '\'  <testcase classname="deb-build" name="nginx-module-ok" time="3"/>\''
            )
            suite = ET.parse(dest).getroot()
            self.assertEqual(suite.get("failures"), "0")

    def test_escaped_build_output_survives_the_xml_parser(self) -> None:
        # Build logs are full of <, > and & (redirections, C++ templates,
        # "make[2]: *** [objs/Makefile] Error 1"). Unescaped, one of them makes
        # the whole report unparseable and the Tests tab silently empty.
        payload = "error: a<b && c>d \"quoted\" 'single'"
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir) / "build-results.xml"
            log = Path(temp_dir) / "build.log"
            log.write_text(payload)
            result = run_helper(
                f'body=$(junit_escape < "{log}"); '
                f'junit_write_report "{dest}" '
                '"  <testcase classname=\\"deb-build\\" name=\\"m\\" time=\\"1\\">'
                '<failure message=\\"Build failed\\">${body}</failure></testcase>"'
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            suite = ET.parse(dest).getroot()
            self.assertEqual(suite.find("testcase/failure").text, payload)

    def test_failure_body_prefers_real_output_over_set_x_trace(self) -> None:
        # A raw `tail -50` of a set -x build log is all "+ rm -rf /tmp/..."
        # noise, which buries the compiler error the report exists to show.
        with tempfile.TemporaryDirectory() as temp_dir:
            log = Path(temp_dir) / "build.log"
            log.write_text(
                "error: too few arguments to function 'ngx_http_validate_host'\n"
                + "".join(f"+ trace line {i}\n" for i in range(80))
            )
            result = run_helper(f'junit_failure_body "{log}"')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("too few arguments", result.stdout)
            self.assertNotIn("+ trace line", result.stdout)

    def test_failure_body_falls_back_to_raw_tail_when_only_trace(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            log = Path(temp_dir) / "build.log"
            log.write_text("".join(f"+ trace line {i}\n" for i in range(5)))
            result = run_helper(f'junit_failure_body "{log}"')
            self.assertIn("trace line 4", result.stdout)

    def test_failure_body_is_escaped(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            log = Path(temp_dir) / "build.log"
            log.write_text("make[2]: *** [objs/Makefile] Error 1 <a & b>\n")
            result = run_helper(f'junit_failure_body "{log}"')
            self.assertIn("&lt;a &amp; b&gt;", result.stdout)
            self.assertNotIn("<a & b>", result.stdout)

    def test_cohort_loop_reports_and_names_tolerated_failures(self) -> None:
        script = BUILD_SCRIPT.read_text()
        _, _, loop = script.partition("for package_dir in $package_dirs; do")

        # A tolerated failure must still produce a <failure> testcase ...
        self.assertIn('<failure message="Build failed">', loop)
        # ... a report must be written on the normal AND both fatal exits ...
        self.assertEqual(loop.count("junit_write_report"), 3)
        # ... and the packages that did not publish must be named in the log.
        self.assertIn("TOLERATED BUILD FAILURES", loop)
        self.assertIn('printf \'!!!   %s\\n\' "${failed_packages[@]}"', loop)


if __name__ == "__main__":
    unittest.main()
