File names and linter ignores
-----------------------------

``doccmd`` creates temporary files for each code block in the documentation file.
These files are created in the same directory as the documentation file, and are named with the documentation file name and the line number of the code block.
Files are created with a prefix set to the given :option:`doccmd --temporary-file-name-prefix` argument (default ``doccmd``).

You can use this information to ignore files in your linter configuration.

For example, to ignore a rule in all files created by ``doccmd`` in a ``ruff`` configuration in ``pyproject.toml``:

.. code-block:: toml

   [tool.ruff]

   lint.per-file-ignores."*doccmd_*.py" = [
      # Allow hardcoded secrets in documentation.
      "S105",
   ]

To ignore a rule in files created by ``doccmd`` when using ``pylint``, use `pylint-per-file-ignores <https://pypi.org/project/pylint-per-file-ignores/>`_, and a configuration like the following (if using ``pyproject.toml``):

.. code-block:: toml

   [tool.pylint.'MESSAGES CONTROL']

   per-file-ignores = [
      "*doccmd_*.py:invalid-name",
   ]

Custom file name patterns
^^^^^^^^^^^^^^^^^^^^^^^^^

For full control over the temporary file names, use the :option:`doccmd --temporary-file-name-pattern` option.
This allows you to specify a pattern with placeholders that will be replaced when creating the temporary file.

Available placeholders:

- ``{prefix}``: The value of :option:`doccmd --temporary-file-name-prefix` (default ``doccmd``)
- ``{source}``: The sanitized source document filename (dots and dashes replaced with underscores)
- ``{line}``: The line number of the code block
- ``{unique}``: A 4-character unique hex identifier to avoid collisions
- ``{ext}``: The file extension including the dot (e.g., ``.py``)

For example, to create files named like ``myproject_README_L42.py``:

.. code-block:: shell

   $ doccmd --language=python --command="mypy" \
       --temporary-file-name-pattern="{prefix}_{source}_L{line}{ext}" \
       --temporary-file-name-prefix="myproject" \
       README.md

When a pattern is specified, it takes precedence over the default naming scheme.
