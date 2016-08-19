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
from __future__ import division, absolute_import, print_function, unicode_literals
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
    text2 = "\n\n#END_ANY_ASK_OR_ANS\n\\begin{enumerate}\n#ENUM\n\\item\n#ASK \n\nWhat's your name ?\n#ANS \n\nAbraham Lincoln\n#END_ANY_ASK_OR_ANS\n\\item\n#ITEM\n#ASK \n\nHow old are you ?\n\n#ANS \n\nI'm actually very old.\n\n#END_ANY_ASK_OR_ANS\n\\item\n#ITEM\n#ASK \n\nDo you like icecream ?\n\n#ANS \n\nYes, pretty much.\n\n#END_ANY_ASK_OR_ANS\n\\item\n#ITEM\n#ASK \n\nWould you like to eat some...\n\n#END_ANY_ASK_OR_ANS\n\\begin{enumerate}\n#ENUM\n\\item\n#ASK \n\n...chocolate cake ?\n\n#ANS \n\nyes, of course.\n\n#END_ANY_ASK_OR_ANS\n\\item\n#ITEM\n#ASK \n\n...fried spider legs ?\n\n#ANS \n\nI'm afraid not, sorry.\n\n#END_ANY_ASK_OR_ANS\n#END\n\\end{enumerate}\n\n#END_ANY_ASK_OR_ANS\n\\item\n#ITEM\n#ASK \n\nNo more questions.\n\n#ANS \n\nok, have a nice day then.\n\n#END_ANY_ASK_OR_ANS\n#END\n\\end{enumerate}\n\n"
    print(sys.executable)
    this_file = realpath(sys._getframe().f_code.co_filename)
    filename = join(dirname(dirname(this_file)), 'questions.py')

    d = {}
    execfile(filename, d)
    assertEq(d['main'](text), text2)

