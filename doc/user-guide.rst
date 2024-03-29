***************
pTyX user guide
***************

*Copyright © 2009-2013 Nicolas Pourcelot*

=====================
pTyX syntax reference
=====================

Any valid LaTeX file is also a valide pTyX file.

Additionnaly, pTyX include several new directives, using tags.


Generalities
============

All tags start with a `#` character, followed by uppercase letters or underscore.

Tags defining blocks (``#IF``, ``#NEW_MACRO``...) have to be closed using ``#END`` tag.

Arguments must be passed to tags using curly brackets: ``#IF{a == 2}``.

Note that tags can be nested without limitation.


Comments
========

Comments lines starts with a `#` character followed by a space.

Example:

.. code-block:: c

    This is an ordinary \latex line.
    # This is a comment, it won't be parsed.
    # Note the space after the hash symbol, at the begining of the line.
    And this is an other \latex line.

Comments at the end of line must start with a space, then a hash and then another space.

.. code-block:: c

    This is an ordinary \latex line. # And this is a comment.

    
IF, ELIF, ELSE tags
===================

To conditionaly include a block of LaTeX code in a document, use ``#IF``, ``#ELIF`` and ``#ELSE`` tags.


Example:

.. code-block:: c

    #IF{AB == AC == BC}
    ABC is an equilateral triangle
    #ELIF{AB == AC or AB == BC or BC == AC}
    ABC is a (non equilateral) isosceles triangle
    #ELSE
    ABC is not an isosceles triangle
    #END


CASE, ELSE tags
===============

pTyX may compile the same document many times to produce different versions of the same document
(useful for exam tests, for example).

Doing so, it uses an internal counter (``NUM`` python variable),
starting from 0 for the first compiled document, and incrementing for each compilation.

Tag ``#CASE`` allows to generate different text according to document number.




Note that:

.. code-block:: c

    #CASE{0}
    This sentence will only appear in the first compiled document.
    #CASE{1}
    This one will only appear in the second compiled document.
    #ELSE
    And the last one, in all others compiled document (if any).
    #END

is exactly equivalent to:

.. code-block:: c

    #IF{NUM == 0}
    This sentence will only appear in the first compiled document.
    #ELIF{NUM == 1}
    This one will only appear in the second compiled document.
    #ELSE
    And the last one, in all others compiled document (if any).
    #END


Example:

.. code-block:: c

    #CASE{0}
    Sujet A
    #CASE{1}
    Sujet B
    #END


ASSERT tag
==========

#ASSERT{arg1} evaluates arg1 as a python expression and raises an error if arg1 evaluate to False.




=============
Small memento
=============

Tags are sorted by alphabetical order.

* #ANS: Begins an **answer block**.

    This block will be processed if and only if internal variable WITH_ANSWERS is set to True.

    Closed by : #ANS, #ASK_ONLY, #ASK, #END.

* #ANSWER{arg1}: arg1 will be processed if and only if internal variable WITH_ANSWERS is set to True.

* #ASK: Begins a **question block**.

    If **format_ask** is defined, **format_ask** will be applied.

    **format_ask** has to be a python function with exactly one argument.

    Example:

.. code-block:: python

    #PYTHON
    def format_ask(string):
        return r'emph{%s}' % string
    #END

    Closed by : #ANS, #ASK_ONLY, #ASK, #END.

* #ASK: Begins a **question-only block**.

    If **format_ask** is defined, **format_ask** will be applied.

     This block will be processed if and only if internal variable WITH_ANSWERS is set to False.

    Closed by : #ANS, #ASK_ONLY, #ASK, #END.

* #ASSERT{assertion}: Raise an error if assertion is False.

    *assertation* has to be a valid Python expression.

* #CALC{expr}: Evaluate expression using *geophar* parser.

    Note that *geophar* needs to be installed separately.

* #CASE{integer}: Begins a **case** conditional block.

    Block will be processed if and only if internal variable NUM matches given integer.

    Closed by : #CASE, #ELSE, #END.

* #COMMENT: Begins a comment block.

    This block will never be processed.

    Closed by : #END.

* #CONDITIONAL_BLOCK:  Don't use this tag (used for internal purpose only).

    Closed by : #END.

* #DEBUG: Pause compilation and ask user what to do.

    Commands may be executed and values of variables may be displayed before compilation resumes.

* #ELIF{condition}: Following block will be processed only if previous blocks where
    not processed and if condition is True.

    Condition must be a valid python expression.

* #ELSE: Following block will be processed only if previous blocks where
    not processed.

* #EVAL[options]{arg}: Don't use this tag (used for internal purpose only).

* #FREEZE_RANDOM_STATE: Used internally.

* #GEO: Generate a tikz figure from *geophar* instructions.

    Note that *geophar* needs to be installed separately.

    Closed by : #END.

* #IF{condition}: Following block will be processed only if condition is True.

* #IFNUM{integer}{arg}: Process arg only if internal variable NUM matches 
  given integer.

* #LOAD{extension}: Extend pTyX syntax by loading an extension.


            'GCALC':        (0, 0, ['@END']),
            'MACRO':        (0, 1, None),
            'NEW_MACRO':    (0, 1, ['@END']),
            'PICK':         (1, 0, None),
            'PYTHON':       (0, 0, ['@END']),
            'QUESTION':     (0, 1, None),
            'RAND':         (1, 0, None),
            # ROOT isn't a real tag, and is never closed.
            'ROOT':         (0, 0, []),
            'SEED':         (1, 0, None),
            'SHUFFLE':      (0, 0, ['@END']),
            # Do *NOT* consume #END tag, which must be used to end #SHUFFLE block.
            'ITEM':         (0, 0, ['ITEM', 'END']),
            'SIGN':         (0, 0, None),
            'SYMPY':        (0, 0, ['@END']),
            'TABSIGN':      (0, 0, ['@END']),
            'TABVAL':       (0, 0, ['@END']),
            'TABVAR':       (0, 0, ['@END']),
            'TEST':         (1, 2, None),
            '-':            (0, 0, None),
            '+':            (0, 0, None),
            '*':            (0, 0, None),
            '=':            (0, 0, None),
            '?':            (0, 0, None),
            '#':            (0, 0, None),
            }








========
Examples
========

