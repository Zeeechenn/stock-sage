import os
import subprocess
import sys
from pathlib import Path


def test_settings_config_does_not_emit_pydantic_v1_config_warning():
    repo = Path(__file__).resolve().parents[1]
    script = """
import warnings

with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    import backend.config  # noqa: F401

messages = [str(w.message) for w in caught]
if any("class-based `config`" in message for message in messages):
    raise SystemExit("\\n".join(messages))
"""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo)

    subprocess.run(
        [sys.executable, "-c", script],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )


def test_sqlite_path_from_url_resolves_local_database_paths(tmp_path):
    from backend.config import sqlite_path_from_url

    db_path = tmp_path / "stock-sage.db"

    assert sqlite_path_from_url(f"sqlite:///{db_path}") == db_path
    assert sqlite_path_from_url("sqlite:///:memory:") is None
    assert sqlite_path_from_url("postgresql://localhost/mingcang") is None
