|project|
=========

A command line tool for running commands against code blocks in documentation files.
This allows you to run linters, formatters, and other tools against the code blocks in your documentation files.

.. include:: install.rst

.. include:: usage-example.rst

What does it work on?
---------------------

* reStructuredText (``.rst``)

.. code-block:: rst

   .. code-block:: shell

      echo "Hello, world!"

* Markdown (``.md``)

.. note::

   By default, ``.md`` files are treated as MyST files.
   To treat them as Markdown, set :option:`doccmd --myst-extension` to ``".""`` and :option:`doccmd --markdown-extension` to ``".md"``.

.. code-block:: markdown

   ```shell
   echo "Hello, world!"
   ```

* MyST (``.md`` with MyST syntax)

.. code-block:: markdown

   ```{code-block} shell
   echo "Hello, world!"
   ```

   ```{code-cell} shell
   echo "Or this code-cell!"
   ```

* MDX (``.mdx``)

.. note::

   ``.mdx`` files are treated as MDX by default.
   Use :option:`doccmd --mdx-extension` to add more suffixes if needed.

.. code-block:: markdown

   ```javascript
   console.log("Hello, MDX!")
   ```

* Want more? Open an issue!

Formatters and padding
----------------------

Running linters with ``doccmd`` gives you errors and warnings with line numbers that match the documentation file.
It does this by adding padding to the code blocks before running the command.

Some tools do not work well with this padding, and you can choose to obscure the line numbers in order to give the tool the original code block's content without padding, by using the :option:`doccmd --no-pad-file` and :option:`doccmd --no-pad-groups` flags.
See :ref:`using_groups_with_formatters` for more information.

For example, to run ``ruff format`` against the code blocks in a Markdown file, use the following command:

.. code-block:: shell

   $ doccmd --language=python --no-pad-file --no-pad-groups --command="ruff format"

.. include:: file-names-and-linter-ignores.rst

Running commands in parallel
----------------------------

When ``doccmd`` is not writing formatter output back into your documentation files (i.e. you are using ``--no-write-to-file``), you can speed things up by parallelizing both within a document and across documents.

* :option:`doccmd --example-workers` evaluates multiple code blocks from the same document at once.
* :option:`doccmd --document-workers` runs different documents concurrently.

Set either option to ``0`` to auto-detect a worker count based on the number of CPUs on your machine.

For example, ``doccmd --no-write-to-file --example-workers 4 --document-workers 2`` spreads work across two documents, with up to four blocks active per document.
This is handy for CPU-bound linters that only emit diagnostics.

Parallel execution is intentionally disabled whenever :option:`doccmd --write-to-file` is in effect, since ``doccmd`` cannot safely merge formatter changes into the original documents out of order.
Command output might interleave between example workers and document workers, so stick to the default sequential mode when deterministic ``stdout`` / ``stderr`` ordering is important.

Reference
---------

.. toctree::
   :maxdepth: 3

   install
   usage-example
   commands
   file-names-and-linter-ignores
   skip-code-blocks
   group-code-blocks
   contributing
   release-process
   changelog
