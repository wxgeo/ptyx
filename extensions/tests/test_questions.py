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


import sys
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

Or maybe fried spider legs ?

-----------------

I'm afraid not, sorry.

 ================

____________________________________________________________________________

No more questions.

-----------------

ok, have a nice day then.

=================

"""
    text2 = r"""

\begin{enumerate}
#ENUM
#ITEM
\item
#ASK

What's your name ?
#END
#ANS

Abraham Lincoln
#END
#ITEM
\item
#ASK

How old are you ?

#END
#ANS

I'm actually very old.

#END
#ITEM
\item
#ASK

Do you like icecream ?

#END
#ANS

Yes, pretty much.

#END
#ITEM
\item
#ASK

Would you like to eat some...

#END
\begin{enumerate}
#ENUM
#ITEM
\item
#ASK

...chocolate cake ?

#END
#ANS

yes, of course.

#END
#ITEM
\item
#ASK

Or maybe fried spider legs ?

#END
#ANS

I'm afraid not, sorry.

#END
#END
\end{enumerate}

#ITEM
\item
#ASK

No more questions.

#END
#ANS

ok, have a nice day then.

#END
#END
\end{enumerate}

"""
    print(sys.executable)
    this_file = realpath(sys._getframe().f_code.co_filename)
    filename = join(dirname(dirname(this_file)), 'questions.py')

    d = {}
    exec(compile(open(filename).read(), filename, 'exec'), d)
    assertEq(d['main'](text, None), text2)

