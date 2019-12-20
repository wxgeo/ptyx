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
Obviously, pTyX needs a working Python installation.
Python version 3.6 (at least) is required for pTyX to run.

pTyX also needs a working LaTeX installation. Command *pdflatex* must be available in your terminal.

Though not required, the following python libraries are recommanded :
* sympy : http://sympy.org/en/index.html
* geophar : https://github.com/wxgeo/geophar/archive/master.zip

Note that geophar come with its own sympy version embedded, so *you won't need to install sympy yourself*.

You may unzip geophar wherever you like, but you need to edit the *config.py* script to indicate geophar path.
Search for the following lines, and edit them according to your own path :

    # <personnal_configuration>
    param['sympy_path'] = '~/Dropbox/Programmation/geophar/wxgeometrie'
    param['wxgeometrie_path'] = '~/Dropbox/Programmation/geophar'
    # </personnal_configuration>

Nota: *wxgeometrie* is geophar previous name.

Usage
-----

To compile a pTyX file (see below), open a terminal, go to pTyX directory, and write:

    $ python ptyx.py my_file.ptyx

For more options:

    $ python ptyx.py --help


pTyX file specification
-----------------------
A pTyX file is essentially a LaTeX file, with a .ptyx extension, (optionally) some custom commands, and embedded python code.

To include python code in a pTyX file, use the #PYTHON and #END balise.
A special *write()* command is avalaible, to generate on the flow latex code from python.

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

To access any python variable outside python code scope, simply add an hashtag before the variable name.

Any valid python expression can also be evaluated this way, using syntax #{python_expr}.

    $#a\mul#b=#{a*b}$

However, pTyX has also reserved tags, like conditionals statements #IF, #ELSE, #ENDIF...

(More to come...)
