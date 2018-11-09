====================
Introduction to pTyX
====================

-------------
What's pTyX ?
-------------

pTyX is a LaTeX precompilator, written in Python.

Typically, a .ptyx file is a LaTeX template with python code snippets inside.

One single pTyX file may generate many latex documents, with different values.

If pdftex is installed, you can generate directly .pdf files instead.



----------
Usage case
----------

I use pTyX mainly to generate easily exercices with random values.

Since I'm a (quite paranoaic) math teacher, I use it in exams :
in one run, I generate several different problem statements and the corresponding
corrections.

Since it uses sympy library, pTyX has symbolic calculus abilities too.


------------
Installation
------------

Obviously, ptyx needs a working Python installation.
Currently, ptyx has been tested on Python 2.6 and 2.7 only.

Ptyx also needs a working LaTeX installation. Command *pdflatex* must be available in your terminal.

Some Ptyx functionalities require the following python libraries:

    * *sympy* : http://sympy.org/en/index.html
    * *geophar* : https://github.com/wxgeo/geophar/archive/master.zip

.. note:: Since *geophar* comes with its own sympy version embedded, *you won't need to install sympy yourself*.

You may unzip geophar wherever you like, but you need to edit ptyx.py main script to indicate geophar path.
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
A ptyx file is essentially a LaTeX file, with a .ptyx extension,
(optionally) some custom commands, and embedded python code.

To include python code in a ptyx file, use the ``#PYTHON`` and ``#END`` balise.

A special ``write()`` command is avalaible, to generate on the flow latex code from python.

This is a basic example of a ptyx file:

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


Running ptyx
------------

To compile previous ptyx file, save it as **my_file.ptyx** for example, then open a terminal,
go to ptyx directory, and write::

    $ python ptyx.py my_file.ptyx

For more options::

    $ python ptyx.py --help
