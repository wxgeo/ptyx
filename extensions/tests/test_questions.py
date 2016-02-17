"""
QUESTIONS

This extension offers a new syntaw to write tests and answers.

An example:

    === QUESTIONS ===

    What's your name ?
    -------------------

    Abraham Lincoln
    ____________________________________________________________________

    How old are you ?

    -------------------

    I'm actually very old.

    ____________________________________________________________________

    Do you like icecream ?

    -------------------

    Yes, pretty much.

    === END ===
"""

import re, os, sys
from os.path import join, dirname, realpath

from testlib import assertEq


def test_question():
    text = r"""

=== QUESTIONS ===

What's your name ?
-------------------

Abraham Lincoln
_____________________________________________________________________________

How old are you ?

-------------------

I'm actually very old.

_______________________________________________________________________________

Do you like icecream ?

-------------------

Yes, pretty much.

_____________________________________________________________________________

Would you like to eat some...

 == QUESTIONS ==

...chocolate cake ?

---------------

yes, of course.

_______________________________________________________________________________

...fried spider legs ?

-----------------

I'm afraid not, sorry.

 == END ==

____________________________________________________________________________

No more questions.

-----------------

ok, have a nice day then.

=== END ===

"""
    text2 = r"""

\begin{enumerate}
\item
#ASK """ r"""

What's your name ?
#ANSWER """ r"""

Abraham Lincoln
\item
#ASK """ r"""

How old are you ?

#ANSWER """ r"""

I'm actually very old.

\item
#ASK """ r"""

Do you like icecream ?

#ANSWER """ r"""

Yes, pretty much.

\item
#ASK """ r"""

Would you like to eat some...

 \begin{enumerate}
\item
#ASK """ r"""

...chocolate cake ?

#ANSWER """ r"""

yes, of course.

\item
#ASK """ r"""

...fried spider legs ?

#ANSWER """ r"""

I'm afraid not, sorry.

 \end{enumerate}

\item
#ASK """ r"""

No more questions.

#ANSWER """ r"""

ok, have a nice day then.

\end{enumerate}

"""
    print(sys.executable)
    this_file = realpath(sys._getframe().f_code.co_filename)
    filename = join(dirname(dirname(this_file)), 'questions.py')

    d = {}
    execfile(filename, d)
    assertEq(d['main'](text), text2)

