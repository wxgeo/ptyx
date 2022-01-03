r"""
QUESTIONS

This extension offers a new syntax to write tests and answers.

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


Another simpler example, with no enumeration (only one question):

    ~~~~~~~~~~~~~~~~~~~

    1+1=?

    ---------------

    2

    ~~~~~~~~~~~~~~~~~~~
"""

from re import sub, DOTALL, match
from ptyx.extensions import extended_python


def main(text, compiler):
    text = extended_python.main(text, compiler)

    # <<<text for question (optional):::inline answer>>>
    def inline_answer(m):
        content = m.group("content")
        # Don't use | to split as it is commonly used for absolute values in mathematics.
        question, answer, *remaining = content.split(":::")
        if len(remaining) == 0:
            return f"#QUESTION{{{question}}}#ANSWER{{{answer}}}"
        # It's not clear what to do if there are more than one :::.
        print(f"WARNING: ambiguous syntax {content!r}!")
        return f"#ANSWER{{{content}}}"

    text = sub("<{3,}(?P<content>.*?)>{3,}", inline_answer, text)

    # ~~~~~~~~~~~~~~~~~~
    # ~~~~~~~~~~~~~~~~~~
    # Lonely question or some explications
    # (won't be displayed in the version with answers)
    # ~~~~~~~~~~~~~~~~~~
    # ~~~~~~~~~~~~~~~~~~
    text = sub(
        "\n[ \t]*~{3,}[ \t]*\n[ \t]*~{3,}[ \t]*\n(?P<content>.*?)\n[ \t]*~{3,}[ \t]*\n[ \t]*~{3,}[ \t]*\n",
        "\n#ASK_ONLY\n\\g<content>\n#END\n",
        text,
        flags=DOTALL,
    )

    lines = []
    stack = ["ROOT"]

    def close_any_ANS_ASK_blocks(stack, lines):
        while stack[-1] in ("ASK", "ANS", "ASK_ONLY"):
            print(stack)
            stack.pop()
            lines.append("#END")

    for line in text.split("\n"):
        stripped_line = line.strip()
        n = len(stripped_line)
        if n == 0:
            lines.append(line)  # line, not stripped_line (to keep spaces) !
        elif stripped_line == "-":
            # Blank line for answer.
            lines.append("")
            lines.append(r"\dotfill")
        elif stripped_line == n * "_":
            # New question.
            close_any_ANS_ASK_blocks(stack, lines)
            lines.append("#ITEM")
            lines.append(r"\item")
            lines.append("#ASK")
            stack.append("ASK")
        elif stripped_line == n * "-":
            # New answer.
            close_any_ANS_ASK_blocks(stack, lines)
            lines.append("#ANS")
            stack.append("ANS")
        elif stripped_line == n * ".":
            # A block of python code.
            if stack[-1] == "PYTHON":
                stack.pop()
                lines.append("#END")
            else:
                stack.append("PYTHON")
                lines.append("#PYTHON")
        elif stripped_line == n * "~":
            # A block of text, either a lonely question, an explanation or question+answer.
            # ~~~~~~~~~~~~~~~~~
            # lonely question
            # ---------------
            # corresponding answer
            # ~~~~~~~~~~~~~~~~~
            if stack[-1] in ("ASK", "ANS"):
                lines.append("#END")
                stack.pop()
            else:
                lines.append("#ASK")
                stack.append("ASK")
        elif match("=+[ \t]*((SHUFFLE)|[?]*(!+[?]*)+)[ \t]*=+", stripped_line):
            # Open a group of randomly shuffled questions.
            close_any_ANS_ASK_blocks(stack, lines)
            stack.append("SHUFFLE")
            lines.append(r"\begin{enumerate}")
            lines.append(r"#SHUFFLE")
            lines.append(r"#ITEM")
            lines.append(r"\item")
            lines.append(r"#ASK")
            stack.append("ASK")
        elif match("=+[ \t]*((QUESTIONS)|[?]+)[ \t]*=+", stripped_line):
            # Open a group of questions.
            close_any_ANS_ASK_blocks(stack, lines)
            stack.append("QUESTIONS")
            lines.append(r"\begin{enumerate}")
            lines.append(r"#ENUM")
            lines.append(r"#ITEM")
            lines.append(r"\item")
            lines.append(r"#ASK")
            stack.append("ASK")
        elif stripped_line == n * "=":
            if "QUESTIONS" in stack or "SHUFFLE" in stack:
                # End a group of questions.
                close_any_ANS_ASK_blocks(stack, lines)
                assert stack[-1] in ("QUESTIONS", "SHUFFLE"), stack[-1]
                lines.append("#END")
                lines.append(r"\end{enumerate}")
                stack.pop()
            else:
                # A block of text, either a lonely question, an explanation or question+answer.
                # ===============
                # lonely question
                # ---------------
                # corresponding answer
                # ===============
                if stack[-1] in ("ASK", "ANS"):
                    lines.append("#END")
                    stack.pop()
                else:
                    lines.append("#ASK")
                    stack.append("ASK")
        elif match("[ \t]*[*]+[ \t]*EXERCISE[ \t]*[*]+", stripped_line):
            lines.append(r"\section{}")
            lines.append("#ASK")
            stack.append("ASK")
        else:
            lines.append(line)  # line, not stripped_line (to keep spaces) !
    return "\n".join(lines)
