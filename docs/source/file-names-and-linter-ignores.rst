File names and linter ignores
-----------------------------

``doccmd`` creates temporary files for each code block in the documentation file.
These files are created in the same directory as the documentation file, and are named with the documentation file name and the line number of the code block.
Files are created with a prefix set to the given ``--file-name-prefix`` argument (default ``doccmd``).

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

   per-file-ignores = """
   *doccmd_*.py:invalid-name
   """
