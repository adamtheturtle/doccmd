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

Requires Python 3.11+.

.. code-block:: shell

   pip install doccmd

With Homebrew (macOS, Linux, WSL)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Requires `Homebrew`_.

.. code-block:: shell

   brew tap adamtheturtle/doccmd
   brew install doccmd

.. _Homebrew: https://docs.brew.sh/Installation

Usage example
-------------

.. code-block:: shell

   # Run mypy against the Python code blocks in README.md and CHANGELOG.rst
   $ doccmd --language=python --command="mypy" README.md CHANGELOG.rst

   # Run gofmt against the Go code blocks in README.md
   # This will modify the README.md file in place
   $ doccmd --language=go --command="gofmt -w" README.md

What does it work on?
---------------------

* reStructuredText (`.rst`)

.. code-block:: rst

   .. code-block:: shell

      echo "Hello, world!"

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

* Want more? Open an issue!

TODO:

* Add documentation (automated, and link to it, and add pre-commits for Sphinx stuff, update urls.Source)
* Release pre-commit hook
* Verbose mode... "Running command "X" against README.rst example from line ..."
* Option to not delete file
* Document https://sybil.readthedocs.io/en/latest/rest.html#skipping-examples on docrun, and make it work
* https://github.com/simplistix/sybil/blob/master/sybil/parsers/rest/codeblock.py add .. code (not just code block), and same for MyST where it is even more popular

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
