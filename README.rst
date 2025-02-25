|Build Status| |codecov| |PyPI|

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

Pre-built Linux (x86) binaries
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: console

   $ curl --fail -L https://github.com/adamtheturtle/doccmd/releases/download/2025.02.20.7/doccmd-linux -o /usr/local/bin/doccmd &&
       chmod +x /usr/local/bin/doccmd

Using ``doccmd`` as a pre-commit hook
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To run ``doccmd`` with `pre-commit`_, add hooks like the following to your ``.pre-commit-config.yaml``:

.. code-block:: yaml

   -   repo: https://github.com/adamtheturtle/doccmd-pre-commit
       rev: v2025.02.20.7
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

* Want more? Open an issue!

Formatters and padding
----------------------

Running linters with ``doccmd`` gives you errors and warnings with line numbers that match the documentation file.
It does this by adding padding to the code blocks before running the command.

Some tools do not work well with this padding, and you can choose to obscure the line numbers in order to give the tool the original code block's content without padding, by using the ``--no-pad-file`` flag.

File names and linter ignores
-----------------------------

``doccmd`` creates temporary files for each code block in the documentation file.
These files are created in the same directory as the documentation file, and are named with the documentation file name and the line number of the code block.
Files are created with a prefix set to the given ``--file-name-prefix`` argument (default ``doccmd``).

You can use this information to ignore files in your linter configuration.

For example, to ignore a rule in all files created by ``doccmd`` in a ``ruff`` configuration in ``pyproject.toml``:

.. code-block:: toml

   [tool.ruff]

   lint.per-file-ignores."doccmd_*.py" = [
      # Allow hardcoded secrets in documentation.
      "S105",
   ]

Skipping code blocks
--------------------

Code blocks which come just after a comment matching ``skip doccmd[all]: next`` are skipped.

To skip multiple code blocks in a row, use ``skip doccmd[all]: start`` and ``skip doccmd[all]: end`` comments surrounding the code blocks to skip.

Use the ``--skip-marker`` option to set a marker for this particular command which will work as well as ``all``.
For example, use ``--skip-marker="type-check"`` to skip code blocks which come just after a comment matching ``skip doccmd[type-check]: next``.

To skip a code block for each of multiple markers, for example to skip a code block for the ``type-check`` and ``lint`` markers but not all markers, add multiple ``skip doccmd`` comments above the code block.

The skip comment will skip the next code block which would otherwise be run.
This means that if you run ``doccmd`` with ``--language=python``, the Python code block in the following example will be skipped:

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

* Markdown (``.md``)

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
Error messages for grouped code blocks may include lines which do not match the document.

Use the ``--group-marker`` option to set a marker for this particular command which will work as well as ``all``.
For example, use ``--group-marker="type-check"`` to group code blocks which come between comments matching ``group doccmd[type-check]: start`` and ``group doccmd[type-check]: end``.

Full documentation
------------------

See the `full documentation <https://adamtheturtle.github.io/doccmd/>`__.

.. |Build Status| image:: https://github.com/adamtheturtle/doccmd/actions/workflows/ci.yml/badge.svg?branch=main
   :target: https://github.com/adamtheturtle/doccmd/actions
.. |codecov| image:: https://codecov.io/gh/adamtheturtle/doccmd/branch/main/graph/badge.svg
   :target: https://codecov.io/gh/adamtheturtle/doccmd
.. |PyPI| image:: https://badge.fury.io/py/doccmd.svg
   :target: https://badge.fury.io/py/doccmd
.. |minimum-python-version| replace:: 3.11
