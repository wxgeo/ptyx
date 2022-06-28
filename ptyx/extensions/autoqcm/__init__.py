r"""
AutoQCM

This extension enables computer corrected quizzes.

An example:

    #LOAD{autoqcm2}
    #SEED{8737545887}

    ===========================
    sty=my_custom_sty_file
    scores=1 0 0
    mode=all
    ids=~/my_students.csv
    ===========================


    <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

    ======= Mathematics ===========

    * 1+1 =
    - 1
    + 2
    - 3
    - 4

    - another answer

    ======= Litterature ==========

    * "to be or not to be", but who actually wrote that ?
    + W. Shakespeare
    - I. Newton
    - W. Churchill
    - Queen Victoria
    - Some bloody idiot

    * Jean de la Fontaine was a famous French
    - pop singer
    - dancer
    + writer
    - detective
    - cheese maker

    > his son is also famous for
    @{\color{blue}%s}
    - dancing french cancan
    - conquering Honolulu
    - walking for the first time on the moon
    - having breakfast at Tiffany

    + none of the above is correct

    >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>


One may include some PTYX code of course.

    """

import re
from pathlib import Path

from ptyx.extensions import extended_python

from .compile.extend_latex_generator import AutoQCMLatexGenerator
from .compile.generate_ptyx_code import generate_ptyx_code

# from .tools.config_parser import dump


# Note for closing tags:
# '@END' means closing tag #END must be consumed, unlike 'END'.
# So, use '@END_QUESTIONS_BLOCK' to close QUESTIONS_BLOCK,
# but use 'END_QUESTIONS_BLOCK' to close QUESTION, since
# #END_QUESTIONS_BLOCK must not be consumed then (it must close
# QUESTIONS_BLOCK too).


__tags__ = {
    # Tags used to structure MCQ
    "QCM": (0, 0, ["@END_QCM"]),
    "SECTION": (0, 0, ["SECTION", "END_QCM"]),
    "NEW_QUESTION": (0, 0, ["NEW_QUESTION", "CONSECUTIVE_QUESTION", "SECTION", "END_QCM"]),
    "CONSECUTIVE_QUESTION": (0, 0, ["NEW_QUESTION", "CONSECUTIVE_QUESTION", "SECTION", "END_QCM"]),
    "VERSION": (1, 0, ["VERSION", "NEW_QUESTION", "CONSECUTIVE_QUESTION", "SECTION", "END_QCM"]),
    "ANSWERS_BLOCK": (0, 0, ["@END_ANSWERS_BLOCK"]),
    "NEW_ANSWER": (2, 0, ["NEW_ANSWER", "END_ANSWERS_BLOCK"]),
    "ANSWERS_LIST": (2, 0, None),
    # Other tags
    "QCM_HEADER": (1, 0, None),
    "DEBUG_AUTOQCM": (0, 0, None),
    # Deprecated tags
    "L_ANSWERS": (1, 0, None),
}
__latex_generator_extension__ = AutoQCMLatexGenerator


def main(text, compiler):
    # Generation algorithm is the following:
    # 1. Parse AutoQCM code, to convert it to plain pTyX code.
    #    Doing this, we now know the number of questions, the number
    #    of answers per question and the students names.
    #    However, we can't know for know the number of the correct answer for
    #    each question, since questions numbers and answers numbers too will
    #    change during shuffling, when compiling pTyX code (and keeping track of
    #    them through shuffling is not so easy).
    # 2. Generate syntax tree, and then compile pTyX code many times to generate
    #    one test for each student. For each compilation, keep track of correct
    #    answers.
    #    All those data are stored in `latex_generator.autoqcm_data['answers']`.
    #    `latex_generator.autoqcm_data['answers']` is a dict
    #    with the following structure:
    #    {1:  [          <-- test n°1 (test id is stored in NUM)
    #         [0,3,5],   <-- 1st question: list of correct answers
    #         [2],       <-- 2nd question: list of correct answers
    #         [1,5],     ...
    #         ],
    #     2:  [          <-- test n°2
    #         [2,3,4],   <-- 1st question: list of correct answers
    #         [0],       <-- 2nd question: list of correct answers
    #         [1,2],     ...
    #         ],
    #    }

    remove_comments = compiler.syntax_tree_generator.remove_comments

    # First pass, only to include files.
    def include(match):
        file_found = False
        pattern = match.group(1).strip()
        contents = []
        path: Path
        for path in sorted(compiler.dir_path.glob(pattern)):
            if path.is_file():
                file_found = True
                with open(path) as file:
                    file_content = remove_comments(file.read().strip())
                    if file_content[:2].strip() != "*":
                        file_content = "*\n" + file_content
                    lines = []
                    for line in file_content.split("\n"):
                        lines.append(line)
                        if (
                            line.startswith("* ")
                            or line.startswith("> ")
                            or line.startswith("OR ")
                            or line.rstrip() in ("*", ">", "OR")
                        ):
                            prettified_path = path.parent / f"\u001b[36m{path.name}\u001b[0m"
                            lines.append(f'#PRINT{{\u001b[36mIMPORTING\u001b[0m "{prettified_path}"}}')
                    contents.append("\n".join(lines))
        if not file_found:
            print(f"WARNING: no file corresponding to {pattern!r} !")
        return "\n\n" + "\n\n".join(contents) + "\n\n"

    text = re.sub(r"^-- (.+)$", include, text, flags=re.MULTILINE)

    # Call extended_python extension.
    text = extended_python.main(text, compiler)

    code = generate_ptyx_code(text)
    assert isinstance(code, str)
    return code
