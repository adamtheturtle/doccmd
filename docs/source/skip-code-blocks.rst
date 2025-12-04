Skipping code blocks
--------------------

Code blocks which come just after a comment matching ``skip doccmd[all]: next`` are skipped.

To skip multiple code blocks in a row, use ``skip doccmd[all]: start`` and ``skip doccmd[all]: end`` comments surrounding the code blocks to skip.

Use the :option:`doccmd --skip-marker` option to set a marker for this particular command which will work as well as ``all``.
For example, set :option:`doccmd --skip-marker` to ``"type-check"`` to skip code blocks which come just after a comment matching ``skip doccmd[type-check]: next``.

To skip a code block for each of multiple markers, for example to skip a code block for the ``type-check`` and ``lint`` markers but not all markers, add multiple ``skip doccmd`` comments above the code block.

The skip comment will skip the next code block which would otherwise be run.
This means that if you set :option:`doccmd --language` to ``"python"``, the Python code block in the following Markdown or MDX example will be skipped:

.. code-block:: markdown

   <-- skip doccmd[all]: next -->

   ```{code-block} shell
   echo "This will not run because the shell language was not selected"
   ```

   ```{code-block} python
   print("This will be skipped!")
   ```

Therefore it is not recommended to use ``skip doccmd[all]`` and to instead use a more specific marker.
For example, if we set :option:`doccmd --language` to ``"shell"`` and :option:`doccmd --skip-marker` ``"echo"`` the following examples show how to skip code blocks in different formats:

* reStructuredText (``.rst``)

.. code-block:: rst

   .. skip doccmd[echo]: next

   .. code-block:: shell

      echo "This will be skipped!"

   .. code-block:: shell

      echo "This will run"

* Markdown (``.md``) and MDX (``.mdx``)

.. code-block:: markdown

   <-- skip doccmd[echo]: next -->

   ```shell
   echo "This will be skipped!"
   ```

   ```shell
   echo "This will run"
   ```

* MyST (``.md`` with MyST syntax)

.. code-block:: markdown

   % skip doccmd[echo]: next

   ```{code-block} shell
   echo "This will be skipped!"
   ```

   ```{code-block} shell
   echo "This will run"
   ```
