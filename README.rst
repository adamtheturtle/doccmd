|Build Status| |PyPI|

doccmd
======

A command line tool for running commands against code blocks in documentation files.
This allows you to run linters, formatters, and other tools against the code blocks in your documentation files.

.. contents::
   :local:

Installation
------------

With ``pip``
^^^^^^^^^^^^

Requires Python |minimum-python-version|\+.

.. code-block:: shell

   $ pip install doccmd

With Homebrew (macOS, Linux, WSL)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Requires `Homebrew`_.

.. code-block:: shell

   $ brew tap adamtheturtle/doccmd
   $ brew install doccmd

.. _Homebrew: https://docs.brew.sh/Installation

With winget (Windows)
^^^^^^^^^^^^^^^^^^^^^

Requires `winget`_.

.. code-block:: shell

   $ winget install --id adamtheturtle.doccmd --source winget --exact

.. _winget: https://learn.microsoft.com/en-us/windows/package-manager/winget/

Pre-built Linux (x86) binaries
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

   $ curl --fail -L https://github.com/adamtheturtle/doccmd/releases/download/2026.01.31/doccmd-linux -o /usr/local/bin/doccmd &&
       chmod +x /usr/local/bin/doccmd

Pre-built macOS (ARM) binaries
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

   $ curl --fail -L https://github.com/adamtheturtle/doccmd/releases/download/2026.01.31/doccmd-macos -o /usr/local/bin/doccmd &&
       chmod +x /usr/local/bin/doccmd

Pre-built macOS (ARM) binaries
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

   $ curl --fail -L https://github.com/adamtheturtle/doccmd/releases/download/2026.01.31/doccmd-macos -o /usr/local/bin/doccmd &&
       chmod +x /usr/local/bin/doccmd

You may need to remove the quarantine attribute to run the binary:

.. code-block:: console

   $ xattr -d com.apple.quarantine /usr/local/bin/doccmd

Pre-built Windows binaries
^^^^^^^^^^^^^^^^^^^^^^^^^^

Download the Windows executable from the `latest release`_ and place it in a directory on your ``PATH``.

.. _latest release: https://github.com/adamtheturtle/doccmd/releases/latest

With Docker
^^^^^^^^^^^

.. code-block:: console

   $ docker run --rm -v "$(pwd):/workdir" -w /workdir "ghcr.io/adamtheturtle/doccmd" --help

With Nix
^^^^^^^^

Requires `Nix`_.

.. code-block:: shell

   $ nix --extra-experimental-features 'nix-command flakes' run "github:adamtheturtle/doccmd/2026.01.31" -- --help

To avoid passing ``--extra-experimental-features`` every time, `enable flakes`_ permanently.

.. _Nix: https://nixos.org/download/
.. _enable flakes: https://wiki.nixos.org/wiki/Flakes#Enabling_flakes_permanently

Or add to your flake inputs:

.. code-block:: nix

   {
     inputs.doccmd.url = "github:adamtheturtle/doccmd";
   }

Using ``doccmd`` as a pre-commit hook
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To run ``doccmd`` with `pre-commit`_, add hooks like the following to your ``.pre-commit-config.yaml``:

.. code-block:: yaml

   -   repo: https://github.com/adamtheturtle/doccmd-pre-commit
       rev: v2026.1.31
       hooks:
       -   id: doccmd
           args: ["--language", "shell", "--command", "shellcheck --shell=bash"]
           additional_dependencies: ["shellcheck-py"]

.. _pre-commit: https://pre-commit.com

Usage example
-------------

.. code-block:: shell

   # Run mypy against the Python code blocks in README.md and CHANGELOG.rst
   $ doccmd --language=python --command="mypy" README.md CHANGELOG.rst

   # Run gofmt against the Go code blocks in README.md
   # This will modify the README.md file in place
   $ doccmd --language=go --command="gofmt -w" README.md

   # or type less... and search for files in the docs directory
   $ doccmd -l python -c mypy README.md docs/

   # Run ruff format against the code blocks in a Markdown file
   # Don't "pad" the code blocks with newlines - the formatter wouldn't like that.
   # See the documentation about groups for more information.
   $ doccmd --language=python --no-pad-file --no-pad-groups --command="ruff format" README.md

   # Run j2lint against the sphinx-jinja2 code blocks in a MyST file
   $ doccmd --sphinx-jinja2 --no-pad-file --command="j2lint" README.md

What does it work on?
---------------------

* reStructuredText (``.rst``)

.. code-block:: rst

   .. code-block:: shell

      echo "Hello, world!"

   .. code:: shell

      echo "Or this Hello, world!"

* Markdown (``.md``)

By default, ``.md`` files are treated as MyST files.
To treat them as Markdown, use ``--myst-extension=. --markdown-extension=.md``.

.. code-block:: markdown

   ```shell
   echo "Hello, world!"
   ```

* MyST (``.md`` with MyST syntax)

.. code-block:: markdown

   ```{code-block} shell
   echo "Hello, world!"
   ```

   ```{code} shell
   echo "Or this Hello, world!"
   ```

   ```{code-cell} shell
   echo "Or this code-cell!"
   ```

* MDX (``.mdx``)

``.mdx`` files are supported out of the box.
Use ``--mdx-extension`` if you need additional suffixes.

.. code-block:: markdown

   ```javascript
   console.log("Hello, MDX!")
   ```

* Djot (``.dj``)

``.dj`` files are supported out of the box.
Use ``--djot-extension`` if you need additional suffixes.

.. code-block:: markdown

   ```shell
   echo "Hello, Djot!"
   ```

* Norg (``.norg``)

``.norg`` files are supported out of the box.
Use ``--norg-extension`` if you need additional suffixes.

.. code-block:: text

   @code shell
   echo "Hello, Norg!"
   @end

* Want more? Open an issue!

Formatters and padding
----------------------

Running linters with ``doccmd`` gives you errors and warnings with line numbers that match the documentation file.
It does this by adding padding to the code blocks before running the command.

Some tools do not work well with this padding, and you can choose to obscure the line numbers in order to give the tool the original code block's content without padding, by using the ``--no-pad-file`` and ``--no-pad-groups`` flag.
See using_groups_with_formatters_ for more information.

File names and linter ignores
-----------------------------

``doccmd`` creates temporary files for each code block in the documentation file.
These files are created in the same directory as the documentation file, and are named with the documentation file name and the line number of the code block.
Files are created with a prefix set to the given ``--temporary-file-name-prefix`` argument (default ``doccmd``).

You can use this information to ignore files in your linter configuration.

For example, to ignore a rule in all files created by ``doccmd`` in a ``ruff`` configuration in ``pyproject.toml``:

.. code-block:: toml

   [tool.ruff]

   lint.per-file-ignores."doccmd_*.py" = [
      # Allow hardcoded secrets in documentation.
      "S105",
   ]

Running commands in parallel
----------------------------

When ``doccmd`` is not writing formatter output back into your documentation files (i.e. you are using ``--no-write-to-file``), you can speed things up by parallelizing both within a document and across documents.

* ``--example-workers`` evaluates multiple code blocks from the same document at once.
* ``--document-workers`` runs different documents concurrently.

Set either option to ``0`` to auto-detect a worker count based on the number of CPUs on your machine.

For example, ``doccmd --no-write-to-file --example-workers 4 --document-workers 2`` spreads work across two documents, with up to four blocks active per document.
This is handy for CPU-bound linters that only emit diagnostics.

Parallel execution is intentionally disabled whenever ``--write-to-file`` is in effect, since ``doccmd`` cannot safely merge formatter changes into the original documents out of order.
Command output might interleave between example workers and document workers, so stick to the default sequential mode when deterministic stdout/stderr ordering is important.

Skipping code blocks
--------------------

Code blocks which come just after a comment matching ``skip doccmd[all]: next`` are skipped.

To skip multiple code blocks in a row, use ``skip doccmd[all]: start`` and ``skip doccmd[all]: end`` comments surrounding the code blocks to skip.

Use the ``--skip-marker`` option to set a marker for this particular command which will work as well as ``all``.
For example, use ``--skip-marker="type-check"`` to skip code blocks which come just after a comment matching ``skip doccmd[type-check]: next``.

To skip a code block for each of multiple markers, for example to skip a code block for the ``type-check`` and ``lint`` markers but not all markers, add multiple ``skip doccmd`` comments above the code block.

The skip comment will skip the next code block which would otherwise be run.
This means that if you run ``doccmd`` with ``--language=python``, the Python code block in the following Markdown or MDX example will be skipped:

.. code-block:: markdown

   <-- skip doccmd[all]: next -->

   ```{code-block} shell
   echo "This will not run because the shell language was not selected"
   ```

   ```{code-block} python
   print("This will be skipped!")
   ```

Therefore it is not recommended to use ``skip doccmd[all]`` and to instead use a more specific marker.
For example, if we used ``doccmd`` with ``--language=shell`` and ``--skip-marker=echo`` the following examples show how to skip code blocks in different formats:

* reStructuredText (``.rst``)

.. code-block:: rst

   .. skip doccmd[echo]: next

   .. code-block:: shell

      echo "This will be skipped!"

   .. code-block:: shell

      echo "This will run"

* Markdown (``.md``) and MDX (``.mdx``)

.. code-block:: markdown

   <-- skip doccmd[echo]: next -->

   ```shell
   echo "This will be skipped!"
   ```

   ```shell
   echo "This will run"
   ```

* MyST (``.md`` with MyST syntax)

.. code-block:: markdown

   % skip doccmd[echo]: next

   ```{code-block} shell
   echo "This will be skipped!"
   ```

   ```{code-block} shell
   echo "This will run"
   ```

Grouping code blocks
--------------------

Automatic file-level grouping
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``--group-file`` option automatically groups all code blocks of the same language within each file, treating them as a single unit for execution.
This is useful when code blocks are designed to be executed sequentially, such as in MyST notebooks or tutorial documents where later blocks depend on definitions from earlier ones.

When this option is enabled, you don't need to add explicit ``group`` directives - all code blocks in a file are automatically combined.

For example, with ``--group-file``, these blocks work together without any special markup:

.. group doccmd[all]: start

.. code-block:: python

   """Example function which is used in a future code block."""


   def my_function() -> None:
       """Do nothing."""


.. code-block:: python

   my_function()

.. group doccmd[all]: end

Manual grouping with directives
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You might have two code blocks like this:

.. group doccmd[all]: start

.. code-block:: python

   """Example function which is used in a future code block."""


   def my_function() -> None:
       """Do nothing."""


.. code-block:: python

   my_function()

.. group doccmd[all]: end

and wish to type check the two code blocks as if they were one.
By default, this will error as in the second code block, ``my_function`` is not defined.

To treat code blocks as one, use ``group doccmd[all]: start`` and ``group doccmd[all]: end`` comments surrounding the code blocks to group.
Grouped code blocks will not have their contents updated in the documentation file.
Error messages for grouped code blocks may include lines which do not match the document, so code formatters will not work on them.

Use the ``--group-marker`` option to set a marker for this particular command which will work as well as ``all``.
For example, use ``--group-marker="type-check"`` to group code blocks which come between comments matching ``group doccmd[type-check]: start`` and ``group doccmd[type-check]: end``.

Grouping by MDX attributes
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``--group-mdx-by-attribute`` option groups MDX code blocks by the value of a specified attribute.
Code blocks with the same attribute value are grouped together and executed as a single unit.
This is useful for working with MDX files that follow conventions like Docusaurus, where code blocks are grouped using custom attributes.

For example, with ``--group-mdx-by-attribute=group``, these blocks are grouped by their ``group`` attribute value:

.. code-block:: markdown

   ```python group="example1"
   def my_function():
       return "Hello"
   ```

   ```python group="example2"
   def other_function():
       return "World"
   ```

   ```python group="example1"
   result = my_function()
   ```

In this example, the first and third code blocks (both with ``group="example1"``) are grouped together and executed as one unit, while the second block (with ``group="example2"``) is processed separately.

Code blocks without the specified attribute are processed individually as normal.

This option only applies to MDX files.

.. _using_groups_with_formatters:

Using groups with formatters
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

By default, code blocks in groups will be separated by newlines in the temporary file created.
This means that line numbers from the original document match the line numbers in the temporary file, and error messages will have correct line numbers.
Some tools, such as formatters, may not work well with this separation.
To have just one newline between code blocks in a group, use the ``--no-pad-groups`` option.
If you then want to add extra padding to the code blocks in a group, add invisible code blocks to the document.
Make sure that the language of the invisible code block is the same as the ``--language`` option given to ``doccmd``.

For example:

* reStructuredText (``.rst``)

.. code-block:: rst

   .. invisible-code-block: java

* Markdown (``.md``) and MDX (``.mdx``)

.. code-block:: markdown

   <!-- invisible-code-block: java

   -->

Tools which change the code block content cannot change the content of code blocks inside groups.
By default this will error.
Use the ``--no-fail-on-group-write`` option to emit a warning but not error in this case.

Full documentation
------------------

See the `full documentation <https://adamtheturtle.github.io/doccmd/>`__.

.. |Build Status| image:: https://github.com/adamtheturtle/doccmd/actions/workflows/ci.yml/badge.svg?branch=main
   :target: https://github.com/adamtheturtle/doccmd/actions
.. |PyPI| image:: https://badge.fury.io/py/doccmd.svg
   :target: https://badge.fury.io/py/doccmd
.. |minimum-python-version| replace:: 3.10
