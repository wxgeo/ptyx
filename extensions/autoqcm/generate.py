from string import ascii_letters
import csv
import re

from .parameters import SQUARE_SIZE_IN_CM, CELL_SIZE_IN_CM



def generate_header(identifier=0, questions=(), answers=None, introduction="", options={}, _n_student=None, csv_path=None):
    """Generate the header of a tex file to be scanned later and the associated config.

    identifier is the integer which identifies the sheet.

    questions is either a list (or any iterable) of questions numbers,
    or an integer n (questions number will be automatically generated then:
    1, 2, 3, ..., n).

    answers is either a list (or any iterable) of questions numbers,
    or an integer n≤26 (answers identifiers will be automatically generated then:
    a, b, c, ...).

    options is a dict keys are tuples (column, line) and values are tikz options
    to be passed to corresponding cell in the table for answers.

    _n_student is for test purpose only (select a student number).
    """
    content = []
    write = content.append
    # Header
    write(r"""\documentclass[a4paper,10pt]{article}
        \usepackage[utf8]{inputenc}
        \usepackage{tikz}
        \usepackage[left=1cm,right=1cm,top=1cm,bottom=1cm]{geometry}
        \parindent=0cm
        \newcommand{\tikzscale}{.5}
        \usepackage{pifont}
        \usepackage{textcomp}
        \usepackage{enumitem} % To resume an enumeration.
        % Extrait du paquet fourier.sty
        \newcommand*{\TakeFourierOrnament}[1]{{%
        \fontencoding{U}\fontfamily{futs}\selectfont\char#1}}
        \newcommand*{\decofourleft}{\TakeFourierOrnament{91}}
        \newcommand*{\decofourright}{\TakeFourierOrnament{92}}
        \newcommand*\circled[1]{\tikz[baseline=(char.base)]{
            \node[fill=gray,shape=rectangle,draw,inner sep=2pt] (char) {\color{white}\textbf{#1}};}}
        \newcommand*\squared[1]{\tikz[baseline=(char.base)]{
            \node[shape=circle,fill=blue!20!white,draw,inner sep=2pt] (char) {\textbf{#1}};}}
        \makeatletter
        \newcommand{\simfill}{%
        \leavevmode \cleaders \hb@xt@ .50em{\hss $\sim$\hss }\hfill \kern \z@
        }
        \makeatother
        \newcounter{answerNumber}
        \renewcommand{\thesubsection}{\Alph{subsection}}
        \setenumerate[0]{label=\protect\squared{\arabic*}}
        \begin{document}""")
    # Two top squares to calibrate and identification band between them

    # Top left square.
    write(r"""\begin{{tikzpicture}}[scale={scale}]
        \draw[fill=black] (0,0) rectangle (1,1);
        \end{{tikzpicture}}""".format(scale=SQUARE_SIZE_IN_CM))

    # Identification band
    n = identifier
    write(r"""\hfill
        \begin{{tikzpicture}}[scale={scale}]
        \draw[fill=black] (-1,0) rectangle (0,1);""".format(scale=SQUARE_SIZE_IN_CM))

    for i in range(15):
        write(r"""\draw[fill={color}] ({x1},0) rectangle ({x2},1);
            """.format(color=("black" if n%2 else "white"), x1=i, x2=i+1))
        n = n//2

    write(r"""\draw (15, .5) node [right] {{\tiny{identifier}}};
        \end{{tikzpicture}}
        \hfill""".format(**locals()))

    # Top right square.
    write(r"""\begin{{tikzpicture}}[scale={scale}]
        \draw[fill=black] (0,0) rectangle (1,1);
        \end{{tikzpicture}}
        """.format(scale=SQUARE_SIZE_IN_CM))

    # Header delimiter.

    write(r"""
        \vspace{-.5em}
        \begin{scriptsize}\hfill\textsc{Ne rien écrire ci-dessus.}\hfill\hfill\hfill\textsc{Ne rien écrire ci-dessus.}\hfill\hfil\end{scriptsize}
        """)


    # Generate students list.
    if csv_path:
        try:
            l = []
            l.append(r'''
                \vspace{-1em}
                \begin{center}
                \begin{tikzpicture}[scale=.25]
                \draw [fill=black] (-2,0) rectangle (-1,1) (-1.5,0) node[below] {\tiny\rotatebox{-90}{\texttt{\textbf{Cochez le nom}}}};''')
            with open(csv_path) as g:
                l = list(csv.reader(g))
                n_students = len(l)
                for i, row in enumerate(reversed(l)):
                    name = ' '.join(item.strip() for item in row)
                    if len(name) >= 15:
                        _name = name[:13].strip()
                        if " " not in name[12:13]:
                            _name += "."
                        name = _name
                    a = 2*i
                    b = a + 1
                    c = a + 0.5
                    color = ('black' if _n_student == n_students - i else 'white')
                    l.append(r'''\draw[fill={color}] ({a},0) rectangle ({b},1) ({c},0) node[below]
                        {{\tiny \rotatebox{{-90}}{{\texttt{{{name}}}}}}};'''.format(**locals()))
            b += 1
            l.append(r'''\draw[rounded corners] (-3,2) rectangle ({b}, -6.5);
                \draw[] (-0.5,2) -- (-0.5,-6.5);
                \end{{tikzpicture}}
                \end{{center}}
                \vspace{{-1em}}
                '''.format(**locals()))
        except FileNotFoundError:
            print("Warning: `%s` not found." % csv_path)
            n_students = 0
            l.clear()
        content.extend(l)




    # Generate the table where students will answer.
    scale = CELL_SIZE_IN_CM
    write(r"""
        \simfill
        \vspace{{.5em}}

        \hfill\hfill
        {introduction}
        \begin{{tikzpicture}}[scale={scale}]
        \draw[fill=black] (-1,0) rectangle (0,1);""".format(**locals()))

    if isinstance(questions, int):
        questions = range(1, questions + 1)

    # Not all iterables have a .__len__() method, so calculate it.
    n_questions = 0

    for x1, name in enumerate(questions):
        x2=x1 + 1
        x3=.5*(x1 + x2)
        write(r"""\draw ({x1},0) rectangle ({x2},1) ({x3},0.5) node {{{name}}};""".format(**locals()))
        n_questions += 1

    if isinstance(answers, int):
        answers = ascii_letters[:answers]

    for i, name in enumerate(answers):
        y1 = -i
        y2 = y1 - 1
        y3 = .5*(y1 + y2)
        write(r"""
            \draw (-1,{y1}) rectangle (0,{y2}) (-0.5,{y3}) node {{{name}}};""".format(**locals()))
        for x1 in range(n_questions):
            opt = options.get((x1, i), "")
            x2=x1 + 1
            write(r"""\draw [{opt}] ({x1},{y1}) rectangle ({x2},{y2});""".format(**locals()))

    n_answers = i + 1

    write(r"""\end{tikzpicture}
\hfill\hfill\hfil
""")


    config = {'n_questions': n_questions,
              'n_answers': n_answers,
              'n_students': n_students,
              }

    return content, config



def generate_body(text):
    # TODO: return number of questions and answers
    # to generate the table of answers.

    # Number of questions
    question_number = 0
    # Number of answers per question
    # If the number of answers is not the same for all questions,
    # then the max will be returned.
    n_answers = 0
    answer_number = 0
    content = []
    # Set all flags to False before parsing.
    mode_qcm = group_opened = question_opened = False
    correct_answers = []

    for _line_ in text.split('\n'):
        line = _line_.lstrip()
        if not mode_qcm:
            # -------------------- STARTING QCM ------------------------
            if line.startswith('<<') and not line.strip('< '):
                # Start of Multiple Choice Questions.
                mode_qcm = True
                # Shuffles groups (if any).
                content.append('#SHUFFLE')
            else:
                content.append(_line_)
        else:
            # -------------------- PARSING QCM -------------------------
            if line.startswith('='):
                # Starts a group of questions.
                # By default, questions inside a group are shuffled,
                # and groups are printed in random order.

                # First, close previous group (if any).
                if group_opened:
                    if question_opened:
                        content.append('#END')
                        question_opened = False
                    # End last group of questions.
                    content.append('#END')
                    group_opened = False
                    content.append('\\end{enumerate}')

                # Then, display title.
                title = line.strip('= ')
                content.append('#ITEM')
                content.append('\subsection{%s}' % title)

                # Everything else will happen at first question, not now.
                # (So that some text can be added before writing
                # \begin{enumerate}.)

            elif line.startswith('* ') or line.startswith('> '):
                # This is a new question.
                question_number += 1
                # First, count number of answers for last question,
                # and update maximum number of answers per question.
                n_answers = max(n_answers, answer_number)
                answer_number = 0
                correct_answers.append([])
                # Close last question before opening a new one.
                if question_opened:
                    content.append('#END')
                # Maybe this is the first question of the group.
                if not group_opened:
                    group_opened = True
                    content.append('\\begin{enumerate}[resume]')
                    content.append('#SHUFFLE')
                if line[0] == '*':
                    # (If line starts with '>', question must follow
                    # the last one.)
                    content.append('#ITEM')
                content.append('\\item')
                content.append('\\setcounter{answerNumber}{0}')
                content.append(line[2:])
                # Shuffle answers.
                content.append('#SHUFFLE')
                question_opened = True

            elif line.startswith('- ') or line.startswith('+ '):
                if answer_number == 0:
                    content.append('\n\n')
                answer_number += 1
                assert question_opened
                content.append('#ITEM')
                # Add counter for each answer.
                #char = chr(96 + answer_number)
                content.append('\\stepcounter{answerNumber}')
                content.append('\\circled{\\alph{answerNumber}}~')
                content.append('\\mbox{%s}\\hfill\\hfil' % line[2:])
                if line[0] == '+':
                    correct_answers[-1].append(answer_number)

            # -------------------- ENDING QCM --------------------------
            elif line.startswith('>>') and not line.strip('> '):
                # End of Multiple Choice Questions.
                mode_qcm = False
                # Ending last group...
                if group_opened:
                    if question_opened:
                        content.append('#END')
                        question_opened = False
                    # End last group of questions.
                    content.append('#END')
                    group_opened = False
                    content.append('\\end{enumerate}')
                # Ending groups shuffling...
                content.append('#END')
                # ... bye bye !
            # ----------------------------------------------------------

            else:
                content.append(_line_)

    n_answers = max(n_answers, answer_number)
    if question_opened:
        content.append('#END')
    if group_opened:
        content.append('#END')
    return content, question_number, n_answers



def generate_tex(text, filename='', **kw):
    """Generate a tex file to be scanned later.

    `filename` is a filename without extension.

    Other arguments:

    * `identifier` is the integer which identifies the sheet.

    * `questions` is either a list (or any iterable) of questions numbers,
    or an integer n (questions number will be automatically generated then:
    1, 2, 3, ..., n).

    * `answers` is either a list (or any iterable) of questions numbers,
    or an integer n≤26 (answers identifiers will be automatically generated then:
    a, b, c, ...).

    * `options` is a dict keys are tuples (column, line) and values are tikz options
    to be passed to corresponding cell in the table for answers.

    * `_n_student` is for test purpose only (select a student number).
    """

    if filename.endswith(".tex"):
        filename = filename[:-4]

    # Extract from text the path of the csv file containing students names.
    m=re.match("[ ]*%[ ]*csv:(.*)", text, re.IGNORECASE)
    if m:
        path = m.group(1).strip()
        kw['csv_path'] = path

    body, n_questions, n_answers = generate_body(text)
    content, config = generate_header(questions=n_questions, answers=n_answers, **kw)
    content.extend(body)
    content.append(r"\end{document}")
    # That's all folks !

    tex = '\n'.join(content)
    cfg = """# n_questions is the number of questions.
n_questions = {n_questions}
# n_answers is the number of answers per question.
n_answers = {n_answers}
# Length of students list (0 if no list at all)
n_students = {n_students}""".format(**config)

    # This is mostly for debuging...
    # ...to be removed later ?
    if filename:
        with open("%s.tex" % filename, "w") as f:
            # Header
            f.write(tex)

        # Generate a config file:
        with open("%s.config" % filename, "w") as f:
            # Generate a config file:
            f.write(cfg)

    # Store the configuration at the begining of the pTyX file.
    tex = """#COMMENT
------ AutoQCM configuration -----
%s
#END
%s""" % (cfg, tex)

    return tex
