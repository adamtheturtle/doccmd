"""Release the next version."""

from pathlib import Path

from admin.binaries import make_linux_binaries


def main() -> None:
    """Perform a release."""
    make_linux_binaries(repo_root=Path())


if __name__ == "__main__":
    main()
