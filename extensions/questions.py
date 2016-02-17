"""
QUESTIONS

This extension offers a new syntaw to write tests and answers.

An example:

    <<<<<<<<<<<<<<<<<<<<<<
    This is an easy test.
    >>>>>>>>>>>>>>>>>>>>>>

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

    ==================


An other simpler example:

    <<<<<<<<<<<<<<<<

    1+1=?

    ---------------

    2

    >>>>>>>>>>>>>>>>
"""

import re

def main(text):
    text = re.sub('\n[ ]*[*]+[ ]*EXERCISE[ ]*[*]+', '\n\section{}\n#ASK', text)
    text = re.sub('\n[ ]*[<][<][<][<][<]+', '\n#ASK', text)
    text = re.sub('\n[ ]*[>][>][>][>][>]+', '\n#END_ANY_ASK_OR_ANS', text)
    text = re.sub('\n[ ]*[=]+[ ]*((QUESTIONS)|[?]+)[ ]*[=]+', '\n#END_ANY_ASK_OR_ANS\n\\\\begin{enumerate}\n#ENUM\n\\\\item\n#ASK ', text)
    text = re.sub('\n[ ]*[=]+[ ]*((SHUFFLE)|[?!]|[!?])[ ]*[=]+', '\n#END_ANY_ASK_OR_ANS\n\\\\begin{enumerate}\n#SHUFFLE\n\\\\item\n#ITEM\n#ASK ', text)
    text = re.sub('\n[ ]*([=]+[ ]*END[ ]*[=]+)|([=][=][=][=][=]+)', '\n#END_ANY_ASK_OR_ANS\n#END\n\\\\end{enumerate}', text)
    text = re.sub('\n[ ]*[_][_][_][_][_]+', '\n#END_ANY_ASK_OR_ANS\n\\\\item\n#ITEM\n#ASK ', text)
    text = re.sub('\n[ ]*[-][-][-][-][-]+', '\n#ANS ', text)
    with open('/tmp/ptyx-questions.log', 'w') as f:
        f.write(text)
    return text


