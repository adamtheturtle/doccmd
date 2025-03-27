Changelog
=========

Next
----

2025.03.27
----------

* Add a ``--sphinx-jinja2`` option to evaluate `sphinx-jinja2 <https://sphinx-jinja2.readthedocs.io/en/latest/>`_ blocks.

2025.03.18
----------

* With ``--verbose``, show the command that will be run before the command is run, not after.

2025.03.06
----------

* Support files which are not UTF-8 encoded.
* Support grouping code blocks with ``doccmd group[all]: start`` and ``doccmd group[all]: end`` comments.

2025.02.18
----------

* Re-add support for Python 3.10.

2025.02.17
----------

* Add support for Markdown (not MyST) files.
* Add support for treating groups of code blocks as one.
* Drop support for Python 3.10.

2025.01.11
----------

2024.12.26
----------

2024.11.14
----------

* Skip files where we hit a lexing error.
* Bump Sybil requirement to >= 9.0.0.

2024.11.06.1
------------

* Add a ``--max-depth`` option for recursing into directories.

2024.11.06
----------

* Add options to support given file extensions for source files.
* Add support for passing in directories.

2024.11.05
----------

* Error if files do not have a ``rst`` or ``md`` extension.

2024.11.04
----------

* Add options to control whether a pseudo-terminal is used for running commands in.
* Rename some options to make it clear that they apply to the temporary files created.

2024.10.14
----------

* Add documentation and source links to PyPI.

2024.10.13.1
------------

* Output in color (not yet on Windows).

2024.10.12
----------

* Only log ``--verbose`` messages when the relevant example will be run and is not a skip directive.

2024.10.11
----------

* Use line endings from the original file.
