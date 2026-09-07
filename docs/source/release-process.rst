Release process
===============

Outcomes
~~~~~~~~

* A new ``git`` tag available to install.
* A new package on PyPI.
* A new Homebrew recipe available to install.
* An updated Nix flake (automatically uses the latest ``git`` tag).
* New pre-built binaries for Linux, macOS, and Windows.

Repository secrets
~~~~~~~~~~~~~~~~~~

The release workflow signs and notarizes the macOS binary, which needs five repository secrets.
Setting them is a one-off, repeated when the signing certificate expires.
Binaries signed and notarized before an expiry keep working afterwards, because ``--timestamp`` records that the signature was made while the certificate was valid; only new signatures need a renewed certificate.

Signing certificate
^^^^^^^^^^^^^^^^^^^

``DEVELOPER_ID_APP_CERT_P12_BASE64`` is a ``base64`` encoded PKCS#12 export of a Developer ID Application certificate and its private key.
The export must contain exactly one such identity: the workflow stops rather than guess which one to sign with.
``DEVELOPER_ID_APP_CERT_PASSWORD`` is the password that the export is encrypted with.

.. code-block:: console

   $ base64 -i certificate.p12 | gh secret set DEVELOPER_ID_APP_CERT_P12_BASE64
   $ gh secret set DEVELOPER_ID_APP_CERT_PASSWORD

Notarization credentials
^^^^^^^^^^^^^^^^^^^^^^^^

``notarytool`` authenticates with the Apple ID belonging to the same team as the signing certificate.
Create an app-specific password at `account.apple.com <https://account.apple.com/>`_.

.. code-block:: console

   $ gh secret set APPLE_ID
   $ gh secret set APPLE_TEAM_ID
   $ gh secret set APPLE_APP_PASSWORD

Perform a Release
~~~~~~~~~~~~~~~~~

#. `Install GitHub CLI`_.

#. Perform a release:

   .. code-block:: console
      :substitutions:

      $ gh workflow run release.yml --repo "|github-owner|/|github-repository|"

.. _Install GitHub CLI: https://cli.github.com/
