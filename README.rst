|Build Status| |codecov| |PyPI| |Documentation Status|

doccmd
======

A command line tool for running commands against documentation files.

.. contents::
   :local:

Installation
------------

With `pip`
^^^^^^^^^^

Requires Python 3.10+.

.. code-block:: shell

   pip install doccmd

With Homebrew (macOS, Linux, WSL)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Requires `Homebrew`_.

.. code-block:: shell

   brew tap adamtheturtle/doccmd
   brew install doccmd

.. _Homebrew: https://docs.brew.sh/Installation

Pre-built Linux binaries
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: console

   $ curl --fail -L https://github.com/adamtheturtle/doccmd/releases/download/2024.09.16/doccmd -o /usr/local/bin/doccmd && \
   $ chmod +x /usr/local/bin/doccmd

Using ``doccmd`` as a pre-commit hook
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To run ``doccmd`` with `pre-commit`_, add hooks like the following to your ``.pre-commit-config.yaml``:

.. code-block:: yaml

   -   repo: https://github.com/adamtheturtle/doccmd-pre-commit
       rev: v2024.09.16
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

   # or type less...
   $ doccmd -l python -c mypy README.md CHANGELOG.rst

What does it work on?
---------------------

* reStructuredText (`.rst`)

.. code-block:: rst

   .. code-block:: shell

      echo "Hello, world!"

   .. code:: shell

      echo "Or this Hello, world!"

* Markdown (`.md`)

.. code-block:: markdown

   ```shell
   echo "Hello, world!"
   ```

* MyST (`.md` with MyST syntax)

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

Full documentation
------------------

See the `full documentation <https://doccmd.readthedocs.io/en/latest>`__.

.. |Build Status| image:: https://github.com/adamtheturtle/doccmd/actions/workflows/ci.yml/badge.svg?branch=main
   :target: https://github.com/adamtheturtle/doccmd/actions
.. |codecov| image:: https://codecov.io/gh/adamtheturtle/doccmd/branch/main/graph/badge.svg
   :target: https://codecov.io/gh/adamtheturtle/doccmd
.. |PyPI| image:: https://badge.fury.io/py/doccmd.svg
   :target: https://badge.fury.io/py/doccmd
.. |Documentation Status| image:: https://readthedocs.org/projects/doccmd/badge/?version=latest
   :target: https://doccmd.readthedocs.io/en/latest/?badge=latest
   :alt: Documentation Status
