from __future__ import annotations
import os, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV = os.environ.copy()
ENV["PYTHONPATH"] = str(ROOT / "src")

def run(cmd):
    print("+", " ".join(map(str, cmd)))
    subprocess.run(cmd, check=True, cwd=ROOT, env=ENV)

def main():
    run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"])
    run([sys.executable, "scripts/hostile_contract_probe.py"])
    run([sys.executable, "-m", "openline_reports", "check", "examples/example_investigation.json"])
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "handoff.json"
        run([sys.executable, "-m", "openline_reports", "handoff", "examples/example_investigation.json", "--out", str(out)])
        if not out.exists():
            raise SystemExit("handoff was not created")
    print("release_check: PASS")

if __name__ == "__main__":
    main()
