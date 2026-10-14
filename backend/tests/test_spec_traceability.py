"""The spec-marker convention itself (decision record 0004), tested with pytest's pytester."""

import pytest


def test_spec_marker_is_written_to_junit_xml(pytester):
    pytester.makepyfile(
        """
        import pytest

        @pytest.mark.spec("booking-lifecycle", "Only listed transitions are allowed")
        def test_marked():
            pass
        """
    )
    report = pytester.path / "report.xml"

    result = pytester.runpytest("-p", "no:asyncio", "-p", "tests.conftest", f"--junitxml={report}")

    result.assert_outcomes(passed=1)
    assert (
        '<property name="spec" value="booking-lifecycle: Only listed transitions are allowed"'
        in report.read_text(encoding="utf-8")
    )


def test_malformed_spec_marker_is_a_usage_error(pytester):
    pytester.makepyfile(
        """
        import pytest

        @pytest.mark.spec("booking-lifecycle")
        def test_marked():
            pass
        """
    )

    result = pytester.runpytest("-p", "no:asyncio", "-p", "tests.conftest")

    assert result.ret == pytest.ExitCode.USAGE_ERROR
