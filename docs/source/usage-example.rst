Usage example
-------------

.. code-block:: shell

   # Run mypy against the Python code blocks in README.md and CHANGELOG.rst
   $ doccmd --language=python --command="mypy" README.md CHANGELOG.rst

   # Run gofmt against the Go code blocks in README.md
   # This will modify the README.md file in place
   $ doccmd --language=go --command="gofmt -w" README.md

   # or type less... and search for files in the docs directory
   $ doccmd -l python -c mypy README.md docs/

   # Run ruff format against the code blocks in a Markdown file
   # Don't "pad" the code blocks with newlines - the formatter wouldn't like that.
   # See the documentation about groups for more information.
   $ doccmd --language=python --no-pad-file --no-pad-groups --command="ruff format" README.md

   # Run j2lint against the sphinx-jinja2 code blocks in a MyST file
   $ doccmd --sphinx-jinja2 --no-pad-file --no-pad-groups --command="j2lint" README.md
