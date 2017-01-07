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
import extended_python


def main(text, compiler):
    text = extended_python.main(text, compiler)
    # ~~~~~~~~~~~~~~~~~~
    # ~~~~~~~~~~~~~~~~~~
    # Lonely question or some explications
    # (won't be displayed in the version with answers)
    # ~~~~~~~~~~~~~~~~~~
    # ~~~~~~~~~~~~~~~~~~
    text = sub("\n[ \t]*~{3,}[ \t]*\n[ \t]*~{3,}[ \t]*\n(?P<content>.*?)\n[ \t]*~{3,}[ \t]*\n[ \t]*~{3,}[ \t]*\n",
               "\n#ASK_ONLY\n\g<content>\n#END\n", text, flags=DOTALL)
    # ~~~~~~~~~~~~~~~~~~
    # Lonely question or some explications
    # (will also be displayed in the version with answers)
    # ~~~~~~~~~~~~~~~~~~
    text = sub("\n[ \t]*~{3,}[ \t]*\n(?P<content>.*?)\n[ \t]*~{3,}[ \t]*\n",
               "\n#ASK\n\g<content>\n#END\n", text, flags=DOTALL)
    # ............
    # Python code
    # ............
    text = sub("\n[ \t]*\\.{3,}[ \t]*\n(?P<content>.*?)\n[ \t]*\\.{3,}[ \t]*\n",
               "\n#PYTHON\n\g<content>\n#END\n", text, flags=DOTALL)
    #~ # ------------------
    #~ # Answer
    #~ # ------------------
    #~ def apply_ans_tag(m):
        #~ content = m.group('content')
        #~ if '___' in content or '===' in content or '~~~' in content:
            #~ return m.group()
        #~ else:
            #~ print('<<<toto', content, 'toto>>>')
            #~ return "\n#ANS\n%s\n#END\n" % content

    #~ text = sub("\n[ \t]*\\-{4,}[ \t]*\n(?P<content>.*?)\n[ \t]*\\-{4,}[ \t]*\n",
               #~ apply_ans_tag, text, flags=DOTALL)

    # <<<text for question (optional):::inline answer>>>
    def inline_answer(m):
        content = m.group('content')
        # Don't use | to split as it is commonly used for absolute values in mathematics.
        l = content.split(':::')
        if len(l) == 2:
            return '#QUESTION{%s}#ANSWER{%s}' % tuple(l)
        # It's not clear what to do if there are more than one :::.
        return '#ANSWER{%s}' % content
    text = sub('<{3,}(?P<content>.*?)>{3,}', inline_answer, text)

    text = sub('\n[ \t]*[*]+[ \t]*EXERCISE[ \t]*[*]+', '\n\section{}\n#ASK', text)
    # ==== QUESTIONS ====
    text = sub('\n[ \t]*=+[ \t]*((QUESTIONS)|[?]+)[ \t]*=+[ \t]*(?=\n)',
               '\n\\\\begin{enumerate}\n#ENUM\n\\\\item\n#ASK ', text)
    # ==== SHUFFLE ====
    text = sub('\n[ \t]*=+[ \t]*((SHUFFLE)|[?]!|![?])[ \t]*=+[ \t]*(?=\n)',
               '\n\\\\begin{enumerate}\n#SHUFFLE\n#ITEM\n\\\\item\n#ASK ', text)
    # ===============
    text = sub('\n[ \t]*((=+[ \t]*END[ \t]*=+)|(={3,}))[ \t]*(?=\n)',
               '\n#END\n#END\n\\\\end{enumerate}', text)
    # _______________
    text = sub('\n[ \t]*_{3,}[ \t]*(?=\n)', '\n#END\n#ITEM\n\\\\item\n#ASK ', text)
    # ---------------
    text = sub('\n[ \t]*-{3,}[ \t]*(?=\n)', '\n#END\n#ANS', text)

    # Create blank dotted lines for answers:
    # a line containing only "-" will be converted to a dotted line.
    def f(m):
        return '\n#ASK_ONLY\n%s\n#END\n' % m.group(0).replace('-', '\n\dotfill')
    text = sub('\n([ \t]*-[ \t]*\n)+', f, text)

    return text
