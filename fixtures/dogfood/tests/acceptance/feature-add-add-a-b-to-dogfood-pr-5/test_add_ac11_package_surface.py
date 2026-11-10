"""AC-11: version, metadata, smoke test, full pytest gate."""

from __future__ import annotations

import subprocess
from pathlib import Path

import dogfood


def test_ac11_version_unchanged() -> None:
    assert dogfood.__version__ == "0.1.0"


def test_ac11_pyproject_metadata() -> None:
    root = Path(__file__).resolve().parents[3]
    text = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert 'name = "dogfood"' in text
    assert 'version = "0.1.0"' in text
    assert 'requires-python = ">=3.11"' in text
    assert "dependencies = []" in text


def test_ac11_single_src_module_file() -> None:
    root = Path(__file__).resolve().parents[3]
    py_files = list((root / "src").rglob("*.py"))
    assert py_files == [root / "src" / "dogfood" / "__init__.py"]


def test_ac11_smoke_test_still_asserts_ping() -> None:
    root = Path(__file__).resolve().parents[3]
    text = (root / "tests" / "test_smoke.py").read_text(encoding="utf-8")
    assert 'assert ping() == "pong"' in text


def test_ac11_full_pytest_gate_exits_zero() -> None:
    repo_root = Path(__file__).resolve().parents[5]
    dogfood_root = repo_root / "fixtures" / "dogfood"
    proc = subprocess.run(
        [
            "uv",
            "run",
            "--project",
            str(dogfood_root),
            "--group",
            "dev",
            "pytest",
            "-q",
            "--ignore=tests/acceptance",
        ],
        cwd=dogfood_root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
