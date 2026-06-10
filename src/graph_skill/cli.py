"""CLI mirror of the MCP tools (3-view golden rule). Lets a human reproduce/diff exactly
what the LLM does. Same logic via tools.py."""

from __future__ import annotations

import json
from pathlib import Path

import rich
import typer

from . import __version__, tools

app = typer.Typer(help="graph-skill — generate self-contained interactive HTML graphs.", add_completion=False)


@app.command()
def types():
    """List available graph types, classified into purpose categories (+ required params)."""
    rich.print_json(data=tools.types_list())


@app.command()
def find(query: str = typer.Argument(..., help="goal, e.g. '피로 수명' or '3d stress'")):
    """Rank graph types by a free-text goal (keyword search over the taxonomy)."""
    rich.print_json(data=tools.types_find(query))


@app.command()
def schema(graph_type: str = typer.Argument(..., help="e.g. base-xy")):
    """Show a type's input schema, requires[], plugins, and hint."""
    rich.print_json(data=tools.schema_get(graph_type))


@app.command()
def validate(
    infile: Path = typer.Option(..., "--in", help="payload JSON {graph_type?, series, axes, ...}"),
    graph_type: str = typer.Option(None, "--type", help="overrides graph_type in the file"),
):
    """Validate inputs; reports missing[] background params (the gate)."""
    payload = json.loads(infile.read_text(encoding="utf-8-sig"))
    gt = graph_type or payload.get("graph_type")
    if not gt:
        raise typer.BadParameter("graph_type missing (pass --type or include it in the file)")
    rich.print_json(data=tools.validate_inputs(gt, payload))


@app.command()
def render(
    infile: Path = typer.Option(..., "--in", help="payload JSON"),
    out: Path = typer.Option(..., "--out", help="output .html path"),
    graph_type: str = typer.Option(None, "--type"),
    embed_mode: str = typer.Option("standalone", "--embed-mode"),
):
    """Render a single self-contained interactive .html."""
    payload = json.loads(infile.read_text(encoding="utf-8-sig"))
    gt = graph_type or payload.get("graph_type")
    if not gt:
        raise typer.BadParameter("graph_type missing (pass --type or include it in the file)")
    data = {k: v for k, v in payload.items() if k not in ("graph_type", "out_path")}
    rich.print_json(data=tools.render_payload(gt, data, out_path=str(out), embed_mode=embed_mode))


@app.command()
def lint(html: Path = typer.Argument(..., help="path to a rendered .html")):
    """Static self-contained gate: external URLs must be 0, single root."""
    rich.print_json(data=tools.lint_output(str(html)))


@app.command("embed-block")
def embed_block(
    html: Path = typer.Argument(...),
    height: int = typer.Option(520, "--height"),
    caption: str = typer.Option(None, "--caption"),
):
    """Emit a report-write html_embed draft fragment for the rendered file."""
    rich.print_json(data=tools.embed_block(str(html), height, caption))


@app.command()
def ingest(
    infile: Path = typer.Argument(..., help="CSV/TSV file"),
    delimiter: str = typer.Option(None, "--delim"),
    no_header: bool = typer.Option(False, "--no-header"),
    units: bool = typer.Option(False, "--units"),
):
    """Parse equipment raw CSV/TSV into numeric columns."""
    rich.print_json(data=tools.ingest_csv(infile.read_text(encoding="utf-8-sig"), delimiter, not no_header, units))


@app.command()
def resample(
    infile: Path = typer.Option(..., "--in", help="JSON {series:[{name,data}]}"),
    n: int = typer.Option(None, "--n"),
    dt: float = typer.Option(None, "--dt"),
):
    """Resample series onto a uniform grid (linear interp)."""
    p = json.loads(infile.read_text(encoding="utf-8-sig"))
    rich.print_json(data=tools.resample(p.get("series") or [], n, dt))


@app.command()
def smooth(
    infile: Path = typer.Option(..., "--in"),
    method: str = typer.Option("savgol", "--method"),
    window: int = typer.Option(7, "--window"),
    polyorder: int = typer.Option(2, "--polyorder"),
):
    """Smooth series (savgol|moving)."""
    p = json.loads(infile.read_text(encoding="utf-8-sig"))
    rich.print_json(data=tools.smooth(p.get("series") or [], method, window, polyorder))


@app.command()
def version():
    """Print the package version."""
    print(__version__)


if __name__ == "__main__":
    app()
