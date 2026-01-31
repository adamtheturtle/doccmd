Installation
------------

With ``pip``
~~~~~~~~~~~~

Requires Python |minimum-python-version|\+.

.. code-block:: console

   $ pip install doccmd

With Homebrew (macOS, Linux, WSL)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Requires `Homebrew`_.

.. code-block:: console

   $ brew tap adamtheturtle/doccmd
   $ brew install doccmd

.. _Homebrew: https://docs.brew.sh/Installation

With winget (Windows)
~~~~~~~~~~~~~~~~~~~~~

Requires `winget`_.

.. code-block:: console

   $ winget install --id adamtheturtle.doccmd --source winget --exact

.. _winget: https://learn.microsoft.com/en-us/windows/package-manager/winget/

Pre-built Linux (x86) binaries
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: console
   :substitutions:

   $ curl --fail -L "https://github.com/|github-owner|/|github-repository|/releases/download/|release|/doccmd-linux" -o /usr/local/bin/doccmd &&
       chmod +x /usr/local/bin/doccmd

Pre-built macOS (ARM) binaries
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: console
   :substitutions:

   $ curl --fail -L "https://github.com/|github-owner|/|github-repository|/releases/download/|release|/doccmd-macos" -o /usr/local/bin/doccmd &&
       chmod +x /usr/local/bin/doccmd

You may need to remove the quarantine attribute to run the binary:

.. code-block:: console

   $ xattr -d com.apple.quarantine /usr/local/bin/doccmd

Pre-built Windows binaries
~~~~~~~~~~~~~~~~~~~~~~~~~~

Download the Windows executable from the `latest release`_ and place it in a directory on your ``PATH``.

.. _latest release: https://github.com/adamtheturtle/doccmd/releases/latest

With Docker
~~~~~~~~~~~

.. code-block:: console
   :substitutions:

   $ docker run --rm -v "$(pwd):/workdir" -w /workdir "|docker-image|" --help

With Nix
~~~~~~~~

Requires `Nix`_.

.. code-block:: console
   :substitutions:

   $ nix --extra-experimental-features 'nix-command flakes' run "github:|github-owner|/|github-repository|/|release|" -- --help

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
   :substitutions:

   -   repo: https://github.com/adamtheturtle/doccmd-pre-commit
       rev: v|release|
       hooks:
       -   id: doccmd
           args: ["--language", "shell", "--command", "shellcheck --shell=bash"]
           additional_dependencies: ["shellcheck-py"]

.. _pre-commit: https://pre-commit.com
