|project|
=========

A command line tool for running commands against code blocks in documentation files.
This allows you to run linters, formatters, and other tools against the code blocks in your documentation files.

.. include:: install.rst

.. include:: usage-example.rst

What does it work on?
---------------------

* reStructuredText (`.rst`)

.. code-block:: rst

   .. code-block:: shell

      echo "Hello, world!"

* Markdown (`.md`)

.. code-block:: markdown

   ```shell
   echo "Hello, world!"
   ```

* MyST (`.md` with MyST syntax)

.. code-block:: markdown

   ```{code-block} shell
   echo "Hello, world!"
   ```

* Want more? Open an issue!

Formatters and padding
----------------------

Running linters with ``doccmd`` gives you errors and warnings with line numbers that match the documentation file.
It does this by adding padding to the code blocks before running the command.

Some tools do not work well with this padding, and you can choose to obscure the line numbers in order to give the tool the original code block's content without padding, by using the ``--no-pad-file`` flag.

.. include:: file-names-and-linter-ignores.rst

Reference
---------

.. toctree::
   :maxdepth: 3

   install
   usage-example
   commands
   file-names-and-linter-ignores
   skip-code-blocks
   contributing
   release-process
   changelog
