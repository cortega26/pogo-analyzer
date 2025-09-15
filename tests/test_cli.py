import os
import sys
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PYTHONPATH = str(ROOT / 'src')


def test_cli_runs():
    env = os.environ.copy()
    env['PYTHONPATH'] = PYTHONPATH
    result = subprocess.run(
        [sys.executable, '-m', 'pogo_analyzer.cli', '--species', 'Bulbasaur', '--iv', '0', '0', '0', '--level', '1'],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0
    assert 'Bulbasaur' in result.stdout
    assert 'Great League' in result.stdout
