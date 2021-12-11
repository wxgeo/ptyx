#!/usr/bin/env python3

# --------------------------------------
#               Compiler
#    Generate all MCQ versions
# --------------------------------------
#    PTYX
#    Python LaTeX preprocessor
#    Copyright (C) 2009-2020  Nicolas Pourcelot
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA


from functools import partial
from ptyx.printers import sympy2latex
from ptyx.latexgenerator import LatexGenerator
from .header import (
    packages_and_macros,
    ID_band,
    extract_ID_NAME_from_csv,
    extract_NAME_from_csv,
    student_ID_table,
    students_checkboxes,
    IdentifiantError,
)


def _has_option(node, option):
    return option in [opt.strip() for opt in node.options.split(",")]


def _analyze_IDS(ids):
    """Given a list of IDs (str), return:
    - the length of an ID (or raise an error if they don't have the same size),
    - the maximal number of different digits in an ID caracter,
    - a list of sets corresponding to the different digits used for each ID caracter.

    >>> _analyze_IDS(['18', '19', '20', '21'])
    (2, 4, [{'1', '2'}, {'8', '9', '0', '1'}])
     """
    lengths = {len(iD) for iD in ids}
    if len(lengths) != 1:
        print(ids)
        raise IdentifiantError("All students ID must have the same length !")
    ID_length = lengths.pop()
    # On crée la liste de l'ensemble des valeurs possibles pour chaque chiffre.
    digits = [set() for _ in range(ID_length)]
    for iD in ids:
        for i, digit in enumerate(iD):
            digits[i].add(digit)

    max_ndigits = max(len(set_) for set_ in digits)
    return ID_length, max_ndigits, digits


def _detect_ID_format(ids: dict, id_format: str) -> dict:
    """Return IDs and ID format data.

    `ids` is a dictionnary who contains students names and ids.
    `id_format` is a string, specifying a number of digits ('8 digits'...).

    Returned ID format data will consist of:
    - the length of an ID,
    - the maximal number of different digits in an ID caracter,
    - a list of sets corresponding to the different digits used for each ID caracter.
    """
    ID_length = None
    if not ids and not id_format:
        raise RuntimeError("Unknown format for students' IDs.")
    if ids:
        # Analyze the IDs list even if `id_format` is provided.
        # This enables to check the consistency between the IDs list and the
        # given ID format.
        ID_length, max_ndigits, digits = _analyze_IDS(ids)

    if id_format:
        n, ext = id_format.split()
        # Test format syntax
        if ext not in ("digit", "digits"):
            raise ValueError(f"Unknown format : {id_format!r}")
        try:
            n = int(n)
        except ValueError:
            raise ValueError(f"Unknown format : {id_format!r}")
        # Test consistency between format and IDs
        if ID_length is not None and ID_length != n:
            raise IdentifiantError("Identifiers don't match given format !")
        # Generate format data
        ID_length = n
        max_ndigits = 10
        digits = n * [tuple("0123456789")]

    return {"ids": ids, "id_format": (ID_length, max_ndigits, digits)}


class SameAnswerError(RuntimeError):
    pass


# Extend LatexGenerator with new tags.


class AutoQCMLatexGenerator(LatexGenerator):
    """Extension of LatexGenerator handling new tags."""

    def clear(self):
        super().clear()
        # Some tags use cache, for code which don't change between two successive compilation.
        # (Typically, this is used for (most of) the header).
        self.autoqcm_cache = {}
        # Default configuration:
        self.autoqcm_data = {
            "mode": {"default": "some"},
            "correct": {"default": 1},
            "incorrect": {"default": 0},
            "skipped": {"default": 0},
            # 'correct_answers': correct_answers, # {1: [4], 2:[1,5], ...}
            "students": [],
            "id-table-pos": None,
            "ids": {},
            "ordering": {},
            # {NUM: {'questions': [2,1,3...], 'answers': {1: [(2, True), (1, False), (3, True)...], ...}}, ...}
            "boxes": {},  # {NUM: {'tag': 'p4, (23.456, 34.667)', ...}, ...}
            "id_format": None,
        }
        self.current_question = ""

    def _test_singularity_and_append(self, code: str, answers_list: list) -> str:
        code = code.strip()
        if code in answers_list:
            msg = [
                "ERROR: Same answer proposed twice in MCQ !",
                f"Answer {code!r} appeared at least twice for the same question.",
                "Question was:",
                repr(self.current_question),
                "",
                "Nota: if this is really desired behaviour, insert",
                "following lines in the header of the ptyx file:",
                "#PYTHON",
                "ALLOW_SAME_ANSWER_TWICE=True",
                "#END",
            ]
            n = max(len(s) for s in msg)
            stars = (n + 4) * "*"
            print(stars)
            for s in msg:
                print("* " + s)
            print(stars)
            raise SameAnswerError(
                "Same answer proposed twice in MCQ " "(see message above for more information) !"
            )
        else:
            answers_list.append(code)
        return code

    def _autoqcm_shuffle_and_parse_children(self, node, children=None, target="ITEM"):
        if self.context.get("AUTOQCM_KEEP_ALL_VERSIONS"):
            self._parse_children(node.children)
        else:
            self._shuffle_and_parse_children(node, children, target=target)

    def _autoqcm_pick_and_parse_children(self, node, children=None, target="ITEM"):
        if self.context.get("AUTOQCM_KEEP_ALL_VERSIONS"):
            self._parse_children(node.children)
        else:
            self._pick_and_parse_children(node, children, target=target)

    def _parse_QCM_tag(self, node):
        self.write("\n")  # A new line is mandatory here if there is no text before MCQ.
        # ~ self.autoqcm_correct_answers = []
        self.autoqcm_data["ordering"][self.NUM] = {"questions": [], "answers": {}}
        #    self.autoqcm_data['answers'] = {}
        # ~ self.autoqcm_data['question_num'] =
        # Global context for all the MCQ.
        self.autoqcm_context = self.context.copy()
        if _has_option(node, "shuffle"):
            self._autoqcm_shuffle_and_parse_children(node, target="SECTION")
        else:
            self._parse_children(node.children)

    def _parse_SECTION_tag(self, node):
        title = node.options.strip() if node.options else ""
        if title:
            self.write(r"\section{%s}" % title)
        children = node.children
        # Nota: \begin{enumerate} must not be written just after the
        # beginning of the section, since there may be some explanations
        # between the section title and the first question.
        # So, we have to insert it just before the first NEW_QUESTION.
        try:
            i = self._child_index(children, "NEW_QUESTION")
        except ValueError:
            self._parse_children(children)
            return
        self._parse_children(children[:i])
        self.write(r"\begin{enumerate}[resume]")
        self._autoqcm_shuffle_and_parse_children(node, children[i:], target="NEW_QUESTION")
        self.write(r"\end{enumerate}")

    def _parse_NEW_QUESTION_tag(self, node):
        # Each question must be independant, so reset all local variables.
        self.set_new_context(self.autoqcm_context)
        self._autoqcm_pick_and_parse_children(node, children=node.children, target="VERSION")

    def _parse_CONSECUTIVE_QUESTION_tag(self, node):
        # For a consecutive question, the context (ie. local variables) must not be reset.
        self._autoqcm_pick_and_parse_children(node, children=node.children, target="VERSION")

    def _parse_VERSION_tag(self, node):
        """A version of a question. Each question have one or more versions.

        Tag usage: #VERSION{num}
        """
        n = int(node.arg(0))
        self.autoqcm_question_number = n
        # This list is used to test that the same answer is not proposed twice.
        self.autoqcm_answers = []
        data = self.autoqcm_data["ordering"][self.NUM]
        data["questions"].append(n)
        data["answers"][n] = []
        self.context["APPLY_TO_ANSWERS"] = None
        self.context["RAW_CODE"] = None
        self.write(r"\pagebreak[3]\item\filbreak")
        self.write(r"\setcounter{answerNumber}{0}")

        # This is used to improve message error when an error occurred.
        # The question itself is stored to make debugging easier (error messages will
        # display current question).
        # Use `self.current_question` to get current question.
        def remember_last_question(code, latex_generator):
            self.current_question = code
            return code

        # So, we have to find where the question itself ends and the answers start.
        try:
            i = self._child_index(node.children, "ANSWERS_BLOCK")
        except ValueError:
            try:
                i = self._child_index(node.children, "ANSWERS_LIST")
            except ValueError:
                raise RuntimeError(
                    "No answers found after a MCQ question !\n"
                    "Question text:\n"
                    "----------------------------------\n"
                    f"{node.as_text(skip_childs=(0,)).strip()}\n"
                    "----------------------------------\n"
                )
        self._parse_children(
            node.children[1:i], function=partial(remember_last_question, latex_generator=self)
        )
        # This is the end of the question itself.

        # And then, the answers follow.
        self.write("\n\\nopagebreak[4]\n")
        self.write("\n\\begin{minipage}{\\textwidth}\n\\begin{flushleft}")
        self._parse_children(node.children[i:])
        self.write("\\end{flushleft}\n\\end{minipage}")

    def _parse_ANSWERS_BLOCK_tag(self, node):
        self._autoqcm_shuffle_and_parse_children(node, target="NEW_ANSWER")

    def _parse_NEW_ANSWER_tag(self, node):
        """A new answer.

        Tag usage: #NEW_VERSION{num}{is_answer_correct}
        """

        k = int(node.arg(0))
        arg1 = node.arg(1).strip()
        if arg1 == "True":
            is_correct = True
        elif arg1 == "False":
            is_correct = False
        else:
            raise RuntimeError(f"Second #NEW_ANSWER argument must be True or False, not {arg1!r}.")
        n = self.autoqcm_question_number

        self._open_answer(n, k, is_correct)
        # Functions to apply. Last one is applied first:
        # if functions = [f, g, h], then s -> f(g(h(s))).
        functions = []

        # TODO(?): functions should be compiled only once for each question block,
        # not for every answer (though it is probably not be a bottleneck in
        # code execution).
        apply = self.context.get("APPLY_TO_ANSWERS")
        if apply:
            # Apply template or function to every answer.
            # Support:
            # - string templates. Ex: \texttt{%s}
            # - name of the function to apply. Ex: f.
            # In last case, the function must have been defined or imported
            # before.
            if "%s" in apply:
                functions.append(lambda s: (apply % s))
            else:
                # Search for the function name in context.
                functions.append(self.context[apply])

        if self.context.get("RAW_CODE"):
            # Try to emulate verbatim (which is not allowed inside
            # a macro argument in LaTeX).
            def escape(s):
                # Replace \ first !
                s = s.replace("\\", r"\textbackslash<!ø5P3C14Lø?>")
                s = s.replace("~", r"\textasciitilde<!ø5P3C14Lø?>")
                s = s.replace("^", r"\textasciicircum<!ø5P3C14Lø?>")
                s = s.replace("'", r"\textquotesingle<!ø5P3C14Lø?>")
                for char in "#$%&_{}":
                    s = s.replace(char, fr"\{char}")
                s = s.replace("<!ø5P3C14Lø?>", "{}")
                return fr"\texttt{{{s}}}"

            functions.append(escape)

        if not self.context.get("ALLOW_SAME_ANSWER_TWICE"):
            # This function is used to verify that each answer is unique.
            # This avoids proposing twice the same answer by mistake, which
            # may occur easily when using random values.
            functions.append(
                partial(self._test_singularity_and_append, answers_list=self.autoqcm_answers)
            )

        self._parse_children(node.children[2:], function=functions)
        self._close_answer()

    def _open_answer(self, n, k, is_correct):
        # `n` is question number *before* shuffling
        # `k` is answer number *before* shuffling
        # When the pdf with solutions will be generated, incorrect answers
        # will be preceded by a white square, while correct ones will
        # be preceded by a gray one.
        self.write(r"\AutoQCMTab{")
        cb_id = f"Q{n}-{k}"
        if self.WITH_ANSWERS and is_correct:
            self.write(r"\checkBox{gray}{%s}" % cb_id)
        else:
            self.write(r"\checkBox{white}{%s}" % cb_id)
        self.write(r"}{")
        data = self.autoqcm_data["ordering"][self.NUM]
        data["answers"][n].append((k, is_correct))

    def _close_answer(self):
        # Close 'AutoQCMTab{' written by `_parse_NEW_ANSWER_tag()`.
        self.write(r"}\quad" "\n")

    def _parse_ANSWERS_LIST_tag(self, node):
        """This tag generates answers from a python list.

        Tag usage: #L_ANSWERS{list_of_answers}{list_of_correct_answers}

        Example:
        #L_ANSWERS{l}{[l[0]]} or #L_ANSWERS{l}{l[0],}
        When using the last syntax, the coma is mandatory.

        Note that if the elements of the lists are not strings, they will be
        converted automatically to math mode latex code (1/2 -> '$\frac{1}{2}$').
        """

        def eval_and_format_arg(arg_num):
            raw_list = eval(node.arg(arg_num).strip(), self.context)
            if not isinstance(raw_list, (list, tuple)):
                raise RuntimeError(
                    f"In #ANSWERS_LIST, argument {arg_num + 1} must be a list of answers."
                )
            formated_list = [
                (val if isinstance(val, str) else f"${sympy2latex(val)}$") for val in raw_list
            ]
            return formated_list

        answers = eval_and_format_arg(0)
        correct_answers = eval_and_format_arg(1)

        # Test that arguments seem correct
        # (they must be a list of unique answers, and answers must include the correct ones).
        for ans in correct_answers:
            if ans not in answers:
                raise RuntimeError(
                    "#ANSWERS_LIST: correct answer {ans} is not in proposed answers list {answers}!"
                )

        for ans in answers:
            self._test_singularity_and_append(ans, self.autoqcm_answers)
        # answers = self.autoqcm_answers

        # Shuffle and generate LaTeX.
        # randfunc.shuffle(answers)
        self.write("\n\n" r"\begin{minipage}{\textwidth}" "\n")
        n = self.autoqcm_question_number
        for k, ans in enumerate(answers, 1):
            self._open_answer(n, k, ans in correct_answers)
            self.write(ans)
            self._close_answer()
        self.write("\n\n\\end{minipage}")

    def _parse_L_ANSWERS_tag(self, node):
        raise DeprecationWarning(
            "L_ANSWERS tag is not supported anymore.\n"
            "Use #ANSWERS_LIST{list_of_answers}{list_of_correct_answers} instead of "
            "#L_ANSWERS{list_of_answers}{correct_answer}.\n"
            "Example: #L_ANSWERS{l}{l[0]} -> #ANSWERS_LIST{l}{[l[0]]}"
        )

    def _parse_DEBUG_AUTOQCM_tag(self, node):
        data = self.autoqcm_data
        print("---------------------------------------------------------------")
        print("AutoQCM data:")
        print(data)
        print("---------------------------------------------------------------")
        # self.write(data)

    def _parse_QCM_HEADER_tag(self, node):
        """Parse HEADER.

        HEADER raw format is the following:
        ===========================
        sty=my_custom_sty_file
        scores=1 0 0
        mode=all
        ids=~/my_students_ids_and_names.csv
        names=~/my_students_names.csv
        id_format=8 digits
        ===========================
        """
        sty = ""
        #    if self.WITH_ANSWERS:
        #        self.context['format_ask'] = (lambda s: '')
        try:
            check_id_or_name = self.autoqcm_cache["check_id_or_name"]
        except KeyError:
            code = ""

            def format_key(key):
                return key.strip().replace(" ", "_").lower()

            # {alias: standard key name}
            alias = {
                "score": "scores",
                "name": "names",
                "student": "names",
                "students": "names",
                "id": "ids",
                "package": "sty",
                "packages": "sty",
                "id_formats": "id_format",
                "ids_formats": "id_format",
                "ids_format": "id_format",
            }
            # Read config
            config = {}
            for line in node.arg(0).split("\n"):
                if "=" not in line:
                    continue
                key, val = line.split("=", maxsplit=1)
                # Normalize key.
                key = format_key(key)
                key = alias.get(key, key)
                config[key] = val.strip()

            if "scores" in config:
                # Set how many points are won/lost for a correct/incorrect answer.
                val = config.pop("scores").replace(",", " ")
                # A correct answer should always give more points than an incorrect one !
                vals: list = sorted(val.split(), key=float)
                self.autoqcm_data["correct"]["default"] = vals[-1]
                if len(vals) > 3:
                    raise ValueError(
                        "`scores` should provide 3 values at most "
                        "(correct answer / incorrect answer / no answer)."
                    )
                if len(vals) >= 2:
                    self.autoqcm_data["incorrect"]["default"] = vals[0]
                    if len(vals) >= 3:
                        self.autoqcm_data["skipped"]["default"] = vals[1]

            if "mode" in config:
                self.autoqcm_data["mode"]["default"] = config.pop("mode")

            if "names" in config:
                # the value must be the path of a CSV file.
                csv = config.pop("names")
                if not self.WITH_ANSWERS:
                    students = extract_NAME_from_csv(csv, str(self.compiler.file_path))
                    code = students_checkboxes(students)
                    self.autoqcm_data["students_list"] = students

            if "ids" in config or "id_format" in config:
                # config['ids'] must be the path of a CSV file.
                csv = config.pop("ids", None)
                id_format = config.pop("id_format", None)

                if not self.WITH_ANSWERS:
                    if csv:
                        ids = extract_ID_NAME_from_csv(csv, str(self.compiler.file_path))
                    else:
                        ids = None

                    try:
                        data = _detect_ID_format(ids, id_format)
                    except IdentifiantError as e:
                        msg = e.args[0]
                        raise IdentifiantError(f"Error in {csv!r} : {msg!r}")

                    self.autoqcm_data.update(data)
                    code = student_ID_table(*data["id_format"])

            if "sty" in config:
                sty = config.pop("sty")

            # Config should be empty by now !
            for key in config:
                raise NameError(f"Unknown key {key!r} in the header of the pTyX file.")

            check_id_or_name = code if not self.WITH_ANSWERS else ""
            self.autoqcm_cache["check_id_or_name"] = check_id_or_name
            check_id_or_name += r"""
            \vspace{1em}

            \tikz{\draw[dotted] ([xshift=2cm]current page.west) -- (current page.east);}
            """

        try:
            header = self.autoqcm_cache["header"]
        except KeyError:
            # TODO: Once using Python 3.6+ (string literals),
            # make packages_and_macros() return a tuple
            # (it's to painful for now because of.format()).
            if sty:
                sty = r"\usepackage{%s}" % sty
            header1, header2 = packages_and_macros()
            header = "\n".join([header1, sty, header2, r"\begin{document}"])
            self.autoqcm_cache["header"] = header

        # Generate barcode
        # Barcode must NOT be put in the cache, since each document has a
        # unique ID.
        n = self.NUM
        calibration = "AUTOQCM__SCORE_FOR_THIS_STUDENT" not in self.context
        barcode = ID_band(ID=n, calibration=calibration)

        self.write("\n".join([header, barcode, check_id_or_name]))
