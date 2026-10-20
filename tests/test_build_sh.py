import subprocess
import unittest
from pathlib import Path

BUILD_SH = Path(__file__).resolve().parent.parent / "scripts" / "build.sh"


def run_build(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(BUILD_SH), *args], capture_output=True, text=True, timeout=30
    )


class BuildArgsTest(unittest.TestCase):
    def test_help_exits_zero(self):
        self.assertEqual(run_build("--help").returncode, 0)

    def test_unknown_option_exits_nonzero(self):
        result = run_build("--bogus")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unknown option: --bogus", result.stderr)

    def test_tag_without_value_exits_nonzero(self):
        result = run_build("--tag")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--tag requires a value", result.stderr)

    def test_invalid_tag_format_rejected(self):
        result = run_build("--tag", "v1.0;rm -rf /")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Invalid tag", result.stderr)


if __name__ == "__main__":
    unittest.main()
