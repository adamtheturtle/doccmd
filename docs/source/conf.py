"""Configuration for Sphinx."""

# pylint: disable=invalid-name

import importlib.metadata
from pathlib import Path

from packaging.specifiers import SpecifierSet
from packaging.version import Version
from sphinx_pyproject import SphinxConfig

_pyproject_file = Path(__file__).parent.parent.parent / "pyproject.toml"
_pyproject_config = SphinxConfig(
    pyproject_file=_pyproject_file,
    config_overrides={"version": None},
)

project = _pyproject_config.name
author = _pyproject_config.author

extensions = [
    "sphinx_copybutton",
    "sphinxcontrib.spelling",
    "sphinx_click.ext",
    "sphinx_inline_tabs",
    "sphinx_substitution_extensions",
]

templates_path = ["_templates"]
source_suffix = ".rst"
master_doc = "index"

project_copyright = f"%Y, {author}"

# Exclude the prompt from copied code with sphinx_copybutton.
# https://sphinx-copybutton.readthedocs.io/en/latest/use.html#automatic-exclusion-of-prompts-from-the-copies.
copybutton_exclude = ".linenos, .gp"

# The version info for the project you're documenting, acts as replacement for
# |release|, also used in various other places throughout the
# built documents.
#
# Use ``importlib.metadata.version`` as per
# https://setuptools-scm.readthedocs.io/en/latest/usage/#usage-from-sphinx.
_version_string = importlib.metadata.version(distribution_name=project)
_version = Version(version=_version_string)
if _version.major == 0:
    msg = (
        f"The version is {_version_string}. "
        "This indicates that the version is not set correctly. "
        "This is likely because the project was built without having all "
        "Git tags available."
    )
    raise ValueError(msg)

# GitHub release tags have the format YYYY.MM.DD, while Python requirement
# versions may have the format YYYY.M.D for single digit months and days.
_num_date_parts = 3
release = ".".join(
    [
        f"{part:02d}" if index < _num_date_parts else str(object=part)
        for index, part in enumerate(iterable=_version.release)
    ]
)

project_metadata = importlib.metadata.metadata(distribution_name=project)
requires_python = project_metadata["Requires-Python"]
specifiers = SpecifierSet(specifiers=requires_python)
(specifier,) = specifiers
if specifier.operator != ">=":
    msg = (
        f"We only support '>=' for Requires-Python, got {specifier.operator}."
    )
    raise ValueError(msg)
minimum_python_version = specifier.version

language = "en"

# The name of the syntax highlighting style to use.
pygments_style = "sphinx"

# Output file base name for HTML help builder.
htmlhelp_basename = "doccmd"
intersphinx_mapping = {
    "python": (f"https://docs.python.org/{minimum_python_version}", None),
}
nitpicky = True
warning_is_error = True

autoclass_content = "both"

html_theme = "furo"
html_title = project
html_show_copyright = False
html_show_sphinx = False
html_show_sourcelink = False
html_theme_options = {
    "sidebar_hide_name": False,
    "source_repository": "https://github.com/adamtheturtle/doccmd/",
    "source_branch": "main",
    "source_directory": "docs/source/",
}

# Retry link checking to avoid transient network errors.
linkcheck_retries = 5

spelling_word_list_filename = "../../spelling_private_dict.txt"

autodoc_member_order = "bysource"

rst_prolog = f"""
.. |project| replace:: {project}
.. |release| replace:: {release}
.. |minimum-python-version| replace:: {minimum_python_version}
.. |github-owner| replace:: adamtheturtle
.. |github-repository| replace:: doccmd
.. |docker-image| replace:: ghcr.io/adamtheturtle/doccmd
"""
