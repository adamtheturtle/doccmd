"""
Create binaries for the CLIs.
"""

import logging
import uuid
from pathlib import Path

import docker
from beartype import beartype
from docker.types import Mount

LOGGER = logging.getLogger(name=__name__)


@beartype
def make_linux_binaries(repo_root: Path) -> None:
    """Create binaries for Linux in a Docker container.

    Args:
        repo_root: The path to the root of the repository.
    """
    client = docker.from_env()
    dist_dir = repo_root / "dist"
    if dist_dir.exists() and set(dist_dir.iterdir()):
        msg = f"Directory {dist_dir} already exists and is not empty."
        raise ValueError(msg)

    code_mount = Mount(
        source=str(object=repo_root.absolute()),
        target="/" + uuid.uuid4().hex,
        type="bind",
    )

    # We install in editable mode to overwrite any potential
    # ``_setuptools_scm_version.txt`` file.
    cmd_in_container = (
        "pip install uv &&"
        "uv pip install --system --editable .[packaging] && "
        "python admin/create_pyinstaller_binaries.py"
    )
    command = f'bash -c "{cmd_in_container}"'

    repository = "python"
    tag = "3.13"
    platform = "linux/amd64"
    image = client.images.pull(
        repository=repository,
        tag=tag,
        platform=platform,
    )
    container = client.containers.run(
        image=image,
        mounts=[code_mount],
        command=command,
        working_dir=code_mount["Target"],
        remove=True,
        detach=True,
        platform=platform,
    )

    for line in container.logs(stream=True):
        warning_line = line.decode().strip()
        LOGGER.warning(warning_line)

    wait_result = container.wait()
    if wait_result["StatusCode"] != 0:
        msg = f"Container exited with status code {wait_result['StatusCode']}."
        raise RuntimeError(msg)
