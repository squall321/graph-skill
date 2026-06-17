"""Every bundled engine/plugin/shell JS must parse (node --check). This is a fast, DOM-free
syntax gate that covers the DOM-rendered engines (review-matrix / flow-core / gauge-core /
playback / schedule) which the headless node_*.mjs suite can't boot — closing the node-side
coverage gap for JS syntax regressions (real-Chromium smoke is the runtime check)."""
import shutil
import subprocess
from pathlib import Path

import pytest

DATA = Path(__file__).resolve().parent.parent / "src" / "graph_skill" / "data"


def _js_files():
    eng = DATA / "engines"
    files = sorted(eng.glob("*/engine.js")) + sorted(eng.glob("*/plugins/*.js"))
    files += sorted((DATA / "shell").glob("*.js"))
    return files


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_all_engine_js_parses():
    files = _js_files()
    assert len(files) >= 30, f"expected the full engine/plugin set, found {len(files)}"
    bad = []
    for f in files:
        r = subprocess.run(["node", "--check", str(f)], capture_output=True, text=True)
        if r.returncode != 0:
            first = r.stderr.strip().splitlines()[0] if r.stderr.strip() else "parse error"
            bad.append(f"{f.relative_to(DATA).as_posix()}: {first}")
    assert not bad, "JS syntax errors:\n  " + "\n  ".join(bad)
