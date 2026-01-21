Contributing to |project|
=========================

Contributions to this repository must pass tests and linting.

CI is the canonical source of truth.

Install contribution dependencies
---------------------------------

Install Python dependencies in a virtual environment.

.. code-block:: console

   $ pip install --editable '.[dev]'

Spell checking requires ``enchant``.
This can be installed on macOS, for example, with `Homebrew`_:

.. code-block:: console

   $ brew install enchant

and on Ubuntu with ``apt``:

.. code-block:: console

   $ apt-get install -y enchant

Install ``pre-commit`` hooks:

.. code-block:: console

   $ prek install

Linting
-------

Run lint tools either by committing, or with:

.. code-block:: console

   $ prek run --all-files --hook-stage pre-commit --verbose
   $ prek run --all-files --hook-stage pre-push --verbose
   $ prek run --all-files --hook-stage manual --verbose

.. _Homebrew: https://brew.sh

Running tests
-------------

Run ``pytest``:

.. code-block:: console

   $ pytest

Documentation
-------------

Documentation is built on Read the Docs.

Run the following commands to build and view documentation locally:

.. code-block:: console

   $ uv run --extra=dev sphinx-build -M html docs/source docs/build -W
   $ python -c 'import os, webbrowser; webbrowser.open("file://" + os.path.abspath("docs/build/html/index.html"))'

Continuous integration
----------------------

Tests are run on GitHub Actions.
The configuration for this is in :file:`.github/workflows/`.

Performing a release
--------------------

See :doc:`release-process`.
