Changelog
=========

Next
----

2026.01.31.1
------------


2026.01.31
----------


- Add support for installing with winget on Windows.

2026.01.28
----------


- Add ``--temporary-file-name-template`` option for customizing temporary file names.
  This allows simpler patterns for linter per-file-ignores, such as ``doccmd_{unique}{suffix}`` to produce files like ``doccmd_a1b2.py``.
- Add ``--respect-gitignore`` / ``--no-respect-gitignore`` option to respect ``.gitignore`` files when discovering files in directories.
  This is enabled by default.
  Files passed directly are not affected by this option.
  This uses `dulwich <https://www.dulwich.io/>`__ and respects ``.gitignore``, ``.git/info/exclude``, and global gitignore files.

2026.01.27.4
------------


2026.01.27.3
------------


2026.01.27.2
------------


2026.01.27.1
------------


2026.01.27
----------


2026.01.25
----------


2026.01.23.4
------------


2026.01.23.3
------------


2026.01.23.2
------------


2026.01.23.1
------------


2026.01.23
----------


2026.01.22.1
------------


2026.01.22
----------


2026.01.21.2
------------


2026.01.21.1
------------


2026.01.21
----------


2026.01.18
----------


2026.01.12
----------


2026.01.03.2
------------


2026.01.03.1
------------

2026.01.03
----------

2025.12.13
----------

2025.12.10
----------

* Add support for Norg files.
* Add support for Djot files.

2025.12.08.5
------------

2025.12.08.4
------------

2025.12.08.3
------------

2025.12.08.2
------------

2025.12.08.1
------------

2025.12.08
----------

2025.12.07
----------

2025.12.05.2
------------

* Error if a group is started but not ended.

2025.12.05.1
------------

2025.12.05
----------

* Add support for MDX files.

2025.12.03
----------

* Add support for MyST ``code-cell`` directive.

2025.11.20
----------

* Add a ``--group-file`` option to automatically group all code blocks of the same language within a file.

2025.11.08.1
------------

2025.11.08
----------

* Add a ``--write-to-file/--no-write-to-file`` option to control whether formatter output is written back to documents.
* Add an ``--example-workers`` option to evaluate multiple code blocks in parallel when using ``--no-write-to-file``.
* Add a ``--document-workers`` option to evaluate multiple documents in parallel when using ``--no-write-to-file``.

2025.10.18
----------

* Add a ``--continue-on-error`` flag to collect and display all errors across files before exiting.

2025.09.19
----------

2025.04.08
----------

* Fix ``IndexError`` when using a formatter which changed the number of lines in a code block.

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
