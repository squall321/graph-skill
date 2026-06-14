"""Regenerate tests/engine_manifest.json — binds each engine's ENGINE_VERSION to a hash of
its source. Refuses to record a code change that didn't also bump ENGINE_VERSION; that
refusal is the structural guard test_gallery_freshness_gate's sibling test relies on. Run
this after bumping an engine version (then commit the manifest). Usage:
    python tests/update_engine_manifest.py
"""
import json
import pathlib

from graph_skill import assets, catalog

MANIFEST = pathlib.Path(__file__).resolve().parent / "engine_manifest.json"


def engines() -> list:
    return sorted({catalog.resolve_type(t).engine for t in catalog.known_types()})


def current() -> dict:
    return {e: {"version": assets.engine_version(e), "code_hash": assets.engine_code_hash(e)}
            for e in engines()}


def main() -> None:
    cur = current()
    old = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.is_file() else {}
    refused = [f"{e}: 코드가 바뀌었는데 ENGINE_VERSION이 그대로 {c['version']} — 먼저 버전을 올리세요"
               for e, c in cur.items()
               if (o := old.get(e)) and o["code_hash"] != c["code_hash"] and o["version"] == c["version"]]
    if refused:
        raise SystemExit("REFUSED (버전 미범프):\n  " + "\n  ".join(refused))
    MANIFEST.write_text(json.dumps(cur, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {MANIFEST.name}: {len(cur)} engines")


if __name__ == "__main__":
    main()
