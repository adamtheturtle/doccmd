"""Configuration for Sphinx."""

# pylint: disable=invalid-name

import datetime
import importlib.metadata

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

year = datetime.datetime.now(tz=datetime.timezone.utc).year
project_copyright = f"{year}, {author}"

# Exclude the prompt from copied code with sphinx_copybutton.
# https://sphinx-copybutton.readthedocs.io/en/latest/use.html#automatic-exclusion-of-prompts-from-the-copies.
copybutton_exclude = ".linenos, .gp"

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# Use ``importlib.metadata.version`` as per
# https://setuptools-scm.readthedocs.io/en/latest/usage/#usage-from-sphinx.
version = importlib.metadata.version(distribution_name=project)
_month, _day, _year, *_ = version.split(".")
release = f"{_month}.{_day}.{_year}"

language = "en"

# The name of the syntax highlighting style to use.
pygments_style = "sphinx"

# Output file base name for HTML help builder.
htmlhelp_basename = "doccmd"
autoclass_content = "init"
intersphinx_mapping = {
    "python": ("https://docs.python.org/3.12", None),
}
nitpicky = True
warning_is_error = True

html_show_copyright = False
html_show_sphinx = False
html_show_sourcelink = False
autoclass_content = "both"

html_theme = "furo"
html_title = project
html_show_copyright = False
html_show_sphinx = False
html_show_sourcelink = False
html_theme_options = {
    "sidebar_hide_name": False,
}

# Retry link checking to avoid transient network errors.
linkcheck_retries = 5

spelling_word_list_filename = "../../spelling_private_dict.txt"

autodoc_member_order = "bysource"

rst_prolog = f"""
.. |project| replace:: {project}
.. |release| replace:: {release}
.. |github-owner| replace:: adamtheturtle
.. |github-repository| replace:: doccmd
"""
