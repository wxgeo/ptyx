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

Tags defining blocks (#IF, #NEW_MACRO...) have to be closed using #END tag.

Arguments must be passed to tags using curly brackets: #IF{a == 2}.


IF, ELIF, ELSE tags
===================

To conditionaly include a block of LaTeX code in a document, use #IF, #ELIF and #ELSE tags.


Example~:

    #IF{AB == AC == BC}
    ABC is an equilateral triangle
    #ELIF{AB == AC or AB == BC or BC == AC}
    ABC is a (non equilateral) isosceles triangle
    #ELSE
    ABC is not an isosceles triangle
    #END


CASE, ELSE tags
===============

pTyX may compile the same document many times to produce different versions of the same document (useful for exam tests, for example).

Doing so, it uses an internal counter (`NUM` python variable), starting from 0 for the first compiled document, and incrementing for each compilation.

Tag #CASE allows




Note that

    #CASE{0}
    This sentence will only appear in the first compiled document.
    #CASE{1}
    This one will only appear in the second compiled document.
    #ELSE
    And the last one, in all others compiled document (if any).
    #END

is exactly equivalent to

    #IF{NUM == 0}
    This sentence will only appear in the first compiled document.
    #IF{NUM == 1}
    This one will only appear in the second compiled document.
    #ELSE
    And the last one, in all others compiled document (if any).
    #END



========
Examples
========

