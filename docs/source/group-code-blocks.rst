Grouping code blocks
--------------------

Automatic file-level grouping
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The :option:`doccmd --group-file` option automatically groups all code blocks of the same language within each file, treating them as a single unit for execution.
This is useful when code blocks are designed to be executed sequentially, such as in MyST notebooks or tutorial documents where later blocks depend on definitions from earlier ones.

When this option is enabled, you don't need to add explicit ``group`` directives - all code blocks in a file are automatically combined.

For example, with :option:`doccmd --group-file`, these blocks work together without any special markup:

.. group doccmd[all]: start

.. code-block:: python

   """Example function which is used in a future code block."""


   def my_function() -> None:
       """Do nothing."""


.. code-block:: python

   my_function()

.. group doccmd[all]: end

Manual grouping with directives
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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

Grouping by MDX attributes
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The :option:`doccmd --group-mdx-by-attribute` option groups MDX code blocks by the value of a specified attribute.
Code blocks with the same attribute value are grouped together and executed as a single unit.
This is useful for working with MDX files that follow conventions like Docusaurus, where code blocks are grouped using custom attributes.

For example, with :option:`doccmd --group-mdx-by-attribute` set to ``"group"``, these blocks are grouped by their ``group`` attribute value:

.. code-block:: markdown

   ```python group="example1"
   def my_function():
       return "Hello"
   ```

   ```python group="example2"
   def other_function():
       return "World"
   ```

   ```python group="example1"
   result = my_function()
   ```

In this example, the first and third code blocks (both with ``group="example1"``) are grouped together and executed as one unit, while the second block (with ``group="example2"``) is processed separately.

Code blocks without the specified attribute are processed individually as normal.

This option only applies to MDX files.

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

* Markdown (``.md``) and MDX (``.mdx``)

.. code-block:: markdown

   <!-- invisible-code-block: java

   -->

Tools which change the code block content cannot change the content of code blocks inside groups.
By default this will error.
Use the :option:`doccmd --no-fail-on-group-write` option to emit a warning but not error in this case.
