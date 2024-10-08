Skipping code blocks
--------------------

Code blocks which come just after a comment matching
``skip doccmd[all]: next`` are skipped.

For example:

* reStructuredText (`.rst`)

.. code-block:: rst

   .. skip doccmd[all]: next

   .. code-block:: shell

      echo "This will be skipped!"

   .. code-block:: shell

      echo "This will run"

* Markdown (`.md`)

.. code-block:: markdown

   <-- skip doccmd[all]: next -->

   ```shell
   echo "This will be skipped!"
   ```

   ```shell
   echo "This will run"
   ```

* MyST (`.md` with MyST syntax)

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
This marker is matched using a regular expression.
