PtYx
====

Overview
--------
PtYx is a LaTeX precompilator, written in Python.
PtYx enables to generate LaTeX documents, using custom commands or plain python code.
One single PtYx file may generate many latex documents, with different values.
I developped and used PtYx to make several different versions of a same test in exams,
for my student, to discourage cheating.
Since it uses sympy library, PtYx has symbolic calculus abilities too.

Installation
------------
Obviously, PtYx needs a working Python installation.
Currently, PtYx has been tested on Python 2.6 and 2.7 only.

PtYx also needs a working LaTeX installation. Command *pdflatex* must be available in your terminal.

PtYx needs some python libraries :
* sympy : http://sympy.org/en/index.html
* geophar : https://github.com/wxgeo/geophar/archive/master.zip

Note that geophar come with its own sympy version embedded, so *you won't need to install sympy yourself*.

You may unzip geophar wherever you like, but you need to edit ptyx.py main script to indicate geophar path.
Search for the following lines, and edit them according to your own path :

    # <personnal_configuration>
    param['sympy_path'] = '~/Dropbox/Programmation/geophar/wxgeometrie'
    param['wxgeometrie_path'] = '~/Dropbox/Programmation/geophar'
    # </personnal_configuration>

Nota: *wxgeometrie* is geophar previous name.

Usage
-----

To compile a ptyx file (see below), open a terminal, go to ptyx directory, and write:

    $ python ptyx.py my_file.ptyx

For more options:

    $ python ptyx.py --help


Ptyx file specification
-----------------------
A ptyx file is essentially a LaTeX file, with a .ptyx extension, (optionally) some custom commands, and embedded python code.

To include python code in a ptyx file, use the #PYTHON and #END balise.
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



(More to come...)
