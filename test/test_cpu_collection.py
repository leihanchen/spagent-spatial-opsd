"""Check that the CI selector discovers new tests and cannot silently skip them."""
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


@pytest.mark.parametrize("body,expected", [
    ("def test_new(): assert True", 0),
    ("def test_new(): assert False", 1),
    ('import pytest\n@pytest.mark.skip(reason="missing dependency")\ndef test_new(): pass', 1),
])
def test_cpu_collection_gate(body, expected, tmp_path):
    directory = tmp_path / "test"
    directory.mkdir()
    shutil.copyfile(Path(__file__).with_name("conftest.py"), directory / "conftest.py")
    (directory / "test_new.py").write_text(body)
    result = subprocess.run([sys.executable, "-m", "pytest", "test", "--cpu-only", "-q"],
                            cwd=tmp_path, capture_output=True, text=True, timeout=30)
    assert result.returncode == expected, result.stdout + result.stderr
