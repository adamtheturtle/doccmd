"""Make PyInstaller binaries for the platform that this is being run on."""

import contextlib
import shutil
import subprocess
import sys
from pathlib import Path

from beartype import beartype


@beartype
def remove_existing_files(scripts: set[Path]) -> None:
    """Remove files created when building binaries.

    This is to stop interference with future builds.
    """
    dist_dir = Path() / "dist"
    build_dir = Path() / "build"

    with contextlib.suppress(FileNotFoundError):
        shutil.rmtree(path=str(dist_dir))

    with contextlib.suppress(FileNotFoundError):
        shutil.rmtree(path=str(build_dir))

    for script in scripts:
        path = Path(script.name + ".spec")
        with contextlib.suppress(FileNotFoundError):
            path.unlink()


@beartype
def create_binary(script: Path) -> None:
    """Use PyInstaller to create a binary from a script.

    Args:
        script: The script to create a binary for.
    """
    pyinstaller_command = [
        "pyinstaller",
        str(script.resolve()),
        "--onefile",
        "--name",
        script.name + "-" + sys.platform,
    ]

    subprocess.check_output(args=pyinstaller_command)


@beartype
def create_binaries() -> None:
    """Make PyInstaller binaries for the platform that this is being run on.

    All binaries will be created in ``./dist``.
    """
    repo_root = Path(__file__).resolve().parent.parent
    script_dir = repo_root / "bin"
    scripts = set(script_dir.iterdir())
    remove_existing_files(scripts=scripts)
    for script in scripts:
        create_binary(script=script)


if __name__ == "__main__":
    create_binaries()
