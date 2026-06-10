"""Equipment raw ingest — parse CSV/TSV text (header + optional units row) into numeric
columns. Generic (covers most Instron/MTS/scope CSV exports); non-numeric cells become None."""

from __future__ import annotations


def parse_csv(text: str, delimiter: str | None = None, header: bool = True,
              units_row: bool = False, comment: str = "#") -> dict:
    lines = [ln for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith(comment)]
    if not lines:
        return {"columns": {}, "names": [], "units": None, "rows": 0}
    if delimiter is None:
        first = lines[0]
        delimiter = "\t" if "\t" in first else ("," if "," in first else (";" if ";" in first else ","))

    def split(ln):
        return [c.strip() for c in ln.split(delimiter)]

    idx, names, units = 0, None, None
    if header:
        names = split(lines[0]); idx = 1
        if units_row and len(lines) > 1:
            units = split(lines[1]); idx = 2
    rows = [split(ln) for ln in lines[idx:]]
    ncol = max((len(r) for r in rows), default=(len(names) if names else 0))
    if not names:
        names = [f"col{i}" for i in range(ncol)]
    cols: dict = {}
    for c, name in enumerate(names):
        vals = []
        for r in rows:
            v = r[c] if c < len(r) else ""
            try:
                vals.append(float(v))
            except ValueError:
                vals.append(None)
        cols[name] = vals
    return {"columns": cols, "names": names, "units": units, "rows": len(rows)}
