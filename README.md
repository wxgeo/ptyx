pTyX
====

Overview
--------
pTyX is a LaTeX precompilator, written in Python.
pTyX enables to generate LaTeX documents, using custom commands or plain python code.
One single pTyX file may generate many latex documents, with different values.
I developped and used pTyX to make several different versions of a same test in exams,
for my student, to discourage cheating.
Since it uses sympy library, pTyX has symbolic calculus abilities too.

Installation
------------
pTyX is only tested on GNU/Linux (Ubuntu), but should work on MacOs X too.

Obviously, pTyX needs a working Python installation.
Python version 3.8 (at least) is required for pTyX to run.

pTyX also needs a working LaTeX installation. Command *pdflatex* must be available in your terminal.

The easiest way to install it is using pip.

    $ pip install ptyx

You may also download and install the latest version from Github:

    $ git clone https://github.com/wxgeo/ptyx.git
    $ cd ptyx
    $ pip install -e .

Usage
-----

To compile a pTyX file (see below), open a terminal, go to pTyX directory, and write:

    $ ptyx my_file.ptyx

For more options:

    $ ptyx --help


pTyX file specification
-----------------------
A pTyX file is essentially a LaTeX file, with a .ptyx extension, (optionally) some custom commands, and embedded python code.

To include python code in a pTyX file, use the #PYTHON and #END balise.
A special *write()* command is available, to generate latex code on the flow from python.

    This a simple \emph{addition}:\quad
    #PYTHON
    from random import randint
    a = randint(5, 9)
    b = randint(2, 4)
    write('%s + %s = %s\\' % (a, b, a + b))
    #END
    Now, some basic \emph{subtraction}:\quad
    #PYTHON
    write('%s - %s = %s\\' % (a, b, a - b))
    #END

To access any python variable outside python code scope, simply add a hashtag before the variable name.

Any valid python expression can also be evaluated this way, using syntax #{python_expr}.

    $#a\mul#b=#{a*b}$

However, pTyX has also reserved tags, like conditionals statements #IF, #ELSE, #ENDIF...

(More to come...)
