File names and linter ignores
-----------------------------

``doccmd`` creates temporary files for each code block in the documentation file.
Each file is created in its own uniquely-named directory alongside the documentation file.
This isolation means that examples running in parallel (see :option:`doccmd --example-workers`) cannot enumerate or race each other's temporary files.
The directory name uses the same prefix as the temporary file (see below), so linter per-file-ignore patterns such as ``*doccmd_*`` continue to match the file's path.
Each directory is made an importable package with an ``__init__.py``, and the generated file name is a valid module name, so linters do not flag it for living in its own directory.

By default, files are named using the pattern ``{prefix}_{source}_l{line}__{unique}_{suffix}``, where:

- ``{prefix}`` is set via :option:`doccmd --temporary-file-name-prefix` (default ``doccmd``)
- ``{source}`` is the sanitized source filename (dots and dashes replaced with underscores, lower-cased)
- ``{line}`` is the line number of the code block
- ``{unique}`` is a short unique identifier
- ``{suffix}`` is the file extension (inferred from the language, or set via :option:`doccmd --temporary-file-extension`)

For example, a Python code block on line 99 of :file:`README.rst` would create a file named :file:`doccmd_readme_rst_l99__a1b2_.py`.

You can customize the file name format using the :option:`doccmd --temporary-file-name-template` option.
This is useful for creating simpler patterns for linter per-file-ignores.

For example, to create simpler file names like :file:`doccmd_a1b2.py`:

.. code-block:: bash

   doccmd --temporary-file-name-template="{prefix}_{unique}{suffix}" ...

You can use this information to ignore files in your linter configuration.

For example, to ignore a rule in all files created by ``doccmd`` in a ``ruff`` configuration in :file:`pyproject.toml`:

.. code-block:: toml

   [tool.ruff]

   lint.per-file-ignores."*doccmd_*.py" = [
      # Allow hardcoded secrets in documentation.
      "S105",
   ]

To ignore a rule in files created by ``doccmd`` when using ``pylint``, use `pylint-per-file-ignores <https://pypi.org/project/pylint-per-file-ignores/>`_, and a configuration like the following (if using :file:`pyproject.toml`):

.. code-block:: toml

   [tool.pylint.'MESSAGES CONTROL']

   per-file-ignores = [
      "*doccmd_*.py:invalid-name",
   ]
