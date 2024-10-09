"""
Tests for creating binaries.
"""

import logging
import sys
from pathlib import Path

import docker
import pytest
from docker.types import Mount

from admin.binaries import make_linux_binaries

LOGGER = logging.getLogger(name=__name__)


@pytest.mark.skipif(
    condition=sys.platform == "win32",
    reason=(
        "GitHub Actions does not support running Linux containers on "
        "Windows. "
        "See https://github.com/actions/runner-images/issues/1143."
    ),
)
def test_linux_binaries(request: pytest.FixtureRequest) -> None:
    """
    ``make_linux_binaries`` creates a binary which can be run on Linux.
    """
    repo_root = request.config.rootpath.absolute()
    dist_dir = repo_root / "dist"
    make_linux_binaries(repo_root=repo_root)
    binary_path_names = {path.name for path in dist_dir.iterdir()}
    assert binary_path_names == {"doccmd-linux"}
    remote_repo_dir = Path("/repo")

    mounts = [
        Mount(
            source=str(repo_root),
            target=str(remote_repo_dir),
            type="bind",
        ),
    ]

    remote_paths: list[Path] = []
    for path in dist_dir.iterdir():
        relative_path = path.relative_to(repo_root)
        remote_path = remote_repo_dir / str(relative_path)
        remote_paths.append(remote_path)

    client = docker.from_env()
    # We use the Python image because this is already pulled when building the
    # image.
    #
    # Because of a click limitation, we do not support running on containers
    # which have LANG and LC_ALL unset.
    repository = "python"
    tag = "3.13"
    platform = "linux/amd64"
    image = client.images.pull(
        repository=repository,
        tag=tag,
        platform=platform,
    )

    for remote_path in remote_paths:
        cmd_in_container = [
            "chmod",
            "+x",
            str(remote_path),
            "&&",
            str(remote_path),
            "--version",
            "&&",
            "rm",
            "-rf",
            str(remote_path),
        ]
        joined_cmd = " ".join(cmd_in_container)
        command = f'bash -c "{joined_cmd}"'
        container = client.containers.run(
            image=image,
            mounts=mounts,
            command=command,
            detach=True,
            platform=platform,
        )

        for line in container.logs(stream=True):
            warning_line = line.decode().strip()
            LOGGER.warning(warning_line)

        container_wait_result = container.wait()

        assert container_wait_result["StatusCode"] == 0
        container.stop()
        container.remove(v=True)
