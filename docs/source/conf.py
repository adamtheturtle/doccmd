"""
Configuration for Sphinx.
"""

# pylint: disable=invalid-name

import importlib.metadata

from packaging.specifiers import SpecifierSet
from packaging.version import Version

project = "doccmd"
author = "Adam Dangoor"

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
# GitHub release tags have the format YYYY.MM.DD, while Python requirement
# versions may have the format YYYY.M.D for single digit months and days.
release = ".".join(f"{part:02d}" for part in _version.release)

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
autoclass_content = "init"
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
    "source_edit_link": "https://github.com/adamtheturtle/doccmd/edit/main/docs/source/{filename}",
    "sidebar_hide_name": False,
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
"""
