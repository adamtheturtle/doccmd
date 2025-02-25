Skipping code blocks
--------------------

Code blocks which come just after a comment matching
``skip doccmd[all]: next`` are skipped.

For example, if we used ``doccmd`` with ``--language=shell``, the following examples show how to skip code blocks in different formats:

* reStructuredText (``.rst``)

.. code-block:: rst

   .. skip doccmd[all]: next

   .. code-block:: shell

      echo "This will be skipped!"

   .. code-block:: shell

      echo "This will run"

* Markdown (``.md``)

.. code-block:: markdown

   <-- skip doccmd[all]: next -->

   ```shell
   echo "This will be skipped!"
   ```

   ```shell
   echo "This will run"
   ```

* MyST (``.md`` with MyST syntax)

.. code-block:: markdown

   % skip doccmd[all]: next

   ```{code-block} shell
   echo "This will be skipped!"
   ```

   ```{code-block} shell
   echo "This will run"
   ```

To skip multiple code blocks in a row, use ``skip doccmd[all]: start`` and ``skip doccmd[all]: end`` surrounding the code blocks to skip.

Use the ``--skip-marker`` option to set a marker for this particular command which will work as well as ``"all"``.
For example, use ``--skip-marker="type-check"`` to skip code blocks which come just after a comment matching ``skip doccmd[type-check]: next``.

To skip a code block for each of multiple markers, for example to skip a code block for the ``type-check`` and ``lint`` markers but not all markers, add multiple ``skip doccmd`` comments above the code block.

The skip marker will skip the next code block which would otherwise be run.
This means that if you run ``doccmd`` with ``--language=python``, the Python code block in the following example will be skipped:

.. code-block:: markdown

   <-- skip doccmd[all]: next -->

   ```{code-block} shell
   echo "This will not run because the shell language was not selected"
   ```

   ```{code-block} python
   print("This will be skipped!")
   ```
