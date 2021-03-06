====================
Introduction to pTyX
====================

-------------
What's pTyX ?
-------------

pTyX is a LaTeX precompilator, written in Python.

Typically, a .pTyX file is a LaTeX template with python code snippets inside.

One single pTyX file may generate many latex documents, with different values.

If pdftex is installed, you can generate directly .pdf files instead.



----------
Usage case
----------

I use pTyX mainly to generate easily exercices with random values.

Since I'm a (maybe paranoaic) math teacher, I use it in exams :
in one run, I generate several different problem statements and the corresponding
corrections.

Since it uses sympy library, pTyX has symbolic calculus abilities too.


------------
Installation
------------

Obviously, pTyX needs a working Python installation.
Currently, pTyX needs Python 3.6 at least.

pTyX also needs a working LaTeX installation. Command *pdflatex* must be available in your terminal.

Some pTyX functionalities require the following python libraries:

    * *sympy* : http://sympy.org/en/index.html
    * *geophar* : https://github.com/wxgeo/geophar/archive/master.zip

.. note:: Since *geophar* comes with its own sympy version embedded, *you won't need to install sympy yourself*.

You may unzip geophar wherever you like, but you need to edit pTyX.py main script to indicate geophar path.
Search for the following lines, and edit them according to your own path::

    # <personnal_configuration>
    param['sympy_path'] = '~/Dropbox/Programmation/geophar/wxgeometrie'
    param['wxgeometrie_path'] = '~/Dropbox/Programmation/geophar'
    # </personnal_configuration>

.. note:: *wxgeometrie* is *geophar* previous name.

---------------------------
Let's start with an example
---------------------------

pTyX file specification
-----------------------
A pTyX file is essentially a LaTeX file, with a .pTyX extension,
(optionally) some custom commands, and embedded python code.

To include python code in a pTyX file, use the ``#PYTHON`` and ``#END`` balise.

A special ``write()`` command is avalaible, to generate on the flow latex code from python.

This is a basic example of a pTyX file:

.. code-block:: latex

    \documentclass[a4paper,10pt]{article}
    \begin{document}
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
    \end{document}


Running pTyX
------------

To compile previous pTyX file, save it as **my_file.pTyX** for example, then open a terminal,
go to pTyX directory, and write::

    $ python pTyX.py my_file.pTyX

For more options::

    $ python pTyX.py --help
