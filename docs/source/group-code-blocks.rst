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

Use the ``--group-marker`` option to set a marker for this particular command which will work as well as ``all``.
For example, use ``--group-marker="type-check"`` to group code blocks which come between comments matching ``group doccmd[type-check]: start`` and ``group doccmd[type-check]: end``.
