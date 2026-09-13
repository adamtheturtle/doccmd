"""Tests for the generated command-line reference."""

from io import StringIO
from pathlib import Path

from sphinx.application import Sphinx


def test_pty_default_in_command_reference(tmp_path: Path) -> None:
    """The terminal mode default is a usable command-line value."""
    source = tmp_path / "source"
    source.mkdir()
    _ = (source / "conf.py").write_text(
        data='extensions = ["sphinx_click.ext"]\n',
        encoding="utf-8",
    )
    _ = (source / "index.rst").write_text(
        data=(
            "Command reference\n=================\n\n"
            ".. click:: doccmd:main\n   :prog: doccmd\n"
        ),
        encoding="utf-8",
    )
    output = tmp_path / "output"
    warnings = StringIO()
    app = Sphinx(
        srcdir=source,
        confdir=source,
        outdir=output,
        doctreedir=tmp_path / "doctrees",
        buildername="text",
        status=None,
        warning=warnings,
        warningiserror=True,
        freshenv=True,
    )
    app.build(force_all=True)

    assert app.statuscode == 0, warnings.getvalue()
    reference = (output / "index.txt").read_text(encoding="utf-8")
    assert '\n   Default:\n      "detect"\n' in reference
