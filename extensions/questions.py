r"""
QUESTIONS

This extension offers a new syntaw to write tests and answers.

An example:

    ~~~~~~~~~~~~~~~~~~~~~
    This is an easy test.
    ~~~~~~~~~~~~~~~~~~~~~

    === QUESTIONS ===

    What's your name ?
    -------------------

    Abraham Lincoln
    ____________________________________________________________________

    How old are you ?

    -------------------

    I'm actually <<<very old>>>.

    ____________________________________________________________________

    Do you like icecream ?

    -------------------

    Yes, pretty much.

    _____________________________________________________________________

    1+1= <<<2>>>

    _____________________________________________________________________

    Complete the multiplication table of binary numbers~:

    ~~~~~~~~~~~~~~~~~~~~~~
    ~~~~~~~~~~~~~~~~~~~~~~
    \begin{tabular}{|c||c|c|}
    \hline
    $\times$ & 0 & 1 \\
    \hline
    \hline
    0        &   &   \\
    \hline
    1        &   &   \\
    \hline
    \end{tabular}
    ~~~~~~~~~~~~~~~~~~~~~~
    ~~~~~~~~~~~~~~~~~~~~~~

    -------------------

    \begin{tabular}{|c||c|c|}
    \hline
    $\times$ & 0 & 1 \\
    \hline
    \hline
    0        & 0 & 0 \\
    \hline
    1        & 0 & 1 \\
    \hline
    \end{tabular}

    ==================


An other simpler example, with no enumeration (only one question):

    ~~~~~~~~~~~~~~~~~~~

    1+1=?

    ---------------

    2

    ~~~~~~~~~~~~~~~~~~~
"""

from __future__ import division, unicode_literals, absolute_import, print_function

from re import sub, DOTALL


def main(text, compiler):
    text = sub("\n[ \t]*~{3,}[ \t]*\n[ \t]*~{3,}[ \t]*\n(?P<content>.*?)\n[ \t]*~{3,}[ \t]*\n[ \t]*~{3,}[ \t]*\n", "\n#ASK_ONLY\n\g<content>\n#END_ANY_ASK_OR_ANS\n", text, flags=DOTALL)
    text = sub("\n[ \t]*~{3,}[ \t]*\n(?P<content>.*?)\n[ \t]*~{3,}[ \t]*\n", "\n#ASK\n\g<content>\n#END_ANY_ASK_OR_ANS\n", text, flags=DOTALL)
    text = sub('<{3,}(?P<content>.*?)>{3,}', '#ANSWER{\g<content>}', text)
    text = sub('\n[ \t]*[*]+[ \t]*EXERCISE[ \t]*[*]+', '\n\section{}\n#ASK', text)
    text = sub('\n[ \t]*=+[ \t]*((QUESTIONS)|[?]+)[ \t]*=+', '\n#END_ANY_ASK_OR_ANS\n\\\\begin{enumerate}\n#ENUM\n\\\\item\n#ASK ', text)
    text = sub('\n[ \t]*=+[ \t]*((SHUFFLE)|[?]!|![?])[ \t]*=+', '\n#END_ANY_ASK_OR_ANS\n\\\\begin{enumerate}\n#SHUFFLE\n#ITEM\n\\\\item\n#ASK ', text)
    text = sub('\n[ \t]*(=+[ \t]*END[ \t]*=+)|(={3,})', '\n#END_ANY_ASK_OR_ANS\n#END\n\\\\end{enumerate}', text)
    text = sub('\n[ \t]*_{3,}', '\n#END_ANY_ASK_OR_ANS\n#ITEM\n\\\\item\n#ASK ', text)
    text = sub('\n[ \t]*-{3,}', '\n#ANS ', text)

    # Create blank dotted lines for answers:
    # a line containing only "-" will be converted to a dotted line.
    def f(m):
        return '\n#ASK_ONLY\n%s\n#END\n' % m.group(0).replace('-', '\n\dotfill')
    text = sub('\n([ \t]*-[ \t]*\n)+', f, text)

    return text
