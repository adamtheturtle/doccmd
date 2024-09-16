Installation
------------

With ``pip``
~~~~~~~~~~~~

Requires Python 3.12+.

.. code-block:: shell

   pip install doccmd

With Homebrew (macOS, Linux, WSL)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Requires `Homebrew`_.

.. code-block:: shell

   brew tap adamtheturtle/doccmd
   brew install doccmd

.. _Homebrew: https://docs.brew.sh/Installation

Pre-built Linux binaries
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: console
   :substitutions:

   $ curl --fail -L https://github.com/|github-owner|/|github-repository|/releases/download/|release|/doccmd -o /usr/local/bin/doccmd && \
   $ chmod +x /usr/local/bin/doccmd

Using ``doccmd`` as a pre-commit hook
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To run ``doccmd`` with `pre-commit`_, add hooks like the following to your ``.pre-commit-config.yaml``:

.. code-block:: yaml

   -   repo: https://github.com/adamtheturtle/doccmd-pre-commit
       rev: v2024.9.11.5
       hooks:
       -   id: doccmd
           args: ["--language", "shell", "--command", "shellcheck --shell=bash"]
           additional_dependencies: ["shellcheck-py"]

.. _pre-commit: https://pre-commit.com
