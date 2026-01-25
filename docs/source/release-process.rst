Release process
===============

Outcomes
~~~~~~~~

* A new ``git`` tag available to install.
* A new package on PyPI.
* A new Homebrew recipe available to install.
* An updated Nix flake (automatically uses the latest ``git`` tag).
* New pre-built binaries for Linux, macOS, and Windows.

Perform a Release
~~~~~~~~~~~~~~~~~

#. `Install GitHub CLI`_.

#. Perform a release:

   .. code-block:: console
      :substitutions:

      $ gh workflow run release.yml --repo "|github-owner|/|github-repository|"

.. _Install GitHub CLI: https://cli.github.com/
