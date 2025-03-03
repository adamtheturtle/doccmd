Grouping code blocks
--------------------

You might have two code blocks like this:

.. group doccmd[all]: start

.. code-block:: python

   """Example function which is used in a future code block."""

   def my_function() -> None:
       """Do nothing."""


.. code-block:: python

   my_function()

.. group doccmd[all]: end

and wish to type check the two code blocks as if they were one.
By default, this will error as in the second code block, ``my_function`` is not defined.

To treat code blocks as one, use ``group doccmd[all]: start`` and ``group doccmd[all]: end`` comments surrounding the code blocks to group.
Grouped code blocks will not have their contents updated in the documentation file.
Error messages for grouped code blocks may include lines which do not match the document.

Use the :option:`doccmd --group-marker` option to set a marker for this particular command which will work as well as ``all``.
For example, set :option:`doccmd --group-marker` to ``"type-check"`` to group code blocks which come between comments matching ``group doccmd[type-check]: start`` and ``group doccmd[type-check]: end``.

.. _using_groups_with_formatters:

Using groups with formatters
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

By default, code blocks in groups will be separated by newlines in the temporary file created.
This means that line numbers from the original document match the line numbers in the temporary file, and error messages will have correct line numbers.
Some tools, such as formatters, may not work well with this separation.
To have just one newline between code blocks in a group, use the :option:`doccmd --no-pad-groups` option.
If you then want to add extra padding to the code blocks in a group, add invisible code blocks to the document.
Make sure that the language of the invisible code block is the same as the :option:`doccmd --language` option given to ``doccmd``.

For example:

* reStructuredText (``.rst``)

.. code-block:: rst

   .. invisible-code-block: java

* Markdown (``.md``)

.. code-block:: markdown

   <!-- invisible-code-block: java

   -->
