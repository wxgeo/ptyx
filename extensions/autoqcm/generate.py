from string import ascii_letters
import csv

from parameters import SQUARE_SIZE_IN_CM, CELL_SIZE_IN_CM



def generate_header(identifier=0, questions=(), answers=None, introduction="", options={}, _n_student=None):
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
    write(r"""
        \documentclass[a4paper,10pt]{article}
        \usepackage[utf8]{inputenc}
        \usepackage{tikz}
        \usepackage[left=1cm,right=1cm,top=1cm,bottom=1cm]{geometry}
        \parindent=0cm
        \newcommand{\tikzscale}{.5}
        \usepackage{pifont}
        \usepackage{textcomp}
        % Extrait du paquet fourier.sty
        \newcommand*{\TakeFourierOrnament}[1]{{%
        \fontencoding{U}\fontfamily{futs}\selectfont\char#1}}
        \newcommand*{\decofourleft}{\TakeFourierOrnament{91}}
        \newcommand*{\decofourright}{\TakeFourierOrnament{92}}
        \makeatletter
        \newcommand{\simfill}{%
        \leavevmode \cleaders \hb@xt@ .50em{\hss $\sim$\hss }\hfill \kern \z@
        }
        \makeatother
        \begin{document}
""")
    # Two top squares to calibrate and identification band between them

    # Top left square.
    write(r"""
        \begin{{tikzpicture}}[scale={scale}]
        \draw[fill=black] (0,0) rectangle (1,1);
        \end{{tikzpicture}}""".format(scale=SQUARE_SIZE_IN_CM)
        )

    # Identification band
    n = identifier
    write(r"""\hfill
        \begin{{tikzpicture}}[scale={scale}]
        \draw[fill=black] (-1,0) rectangle (0,1);
        """.format(scale=SQUARE_SIZE_IN_CM)
        )

    for i in range(15):
        write(r"""\draw[fill={color}] ({x1},0) rectangle ({x2},1);
            """.format(color=("black" if n%2 else "white"), x1=i, x2=i+1))
        n = n//2

    write(r"""\draw (15, .5) node [right] {{\tiny{identifier}}};
        \end{{tikzpicture}}
        \hfill
        """.format(**locals())
        )

    # Top right square.
    write(r"""\begin{{tikzpicture}}[scale={scale}]
        \draw[fill=black] (0,0) rectangle (1,1);
        \end{{tikzpicture}}
        """.format(scale=SQUARE_SIZE_IN_CM)
        )

    # Header delimiter.

    write(r"""

        \vspace{-.5em}
        \begin{scriptsize}\hfill\textsc{Ne rien écrire ci-dessus.}\hfill\hfill\hfill\textsc{Ne rien écrire ci-dessus.}\hfill\hfil\end{scriptsize}

        """)


    # Generate students list.
    try:
        write(r'''

            \vspace{-1em}
            \begin{center}
            \begin{tikzpicture}[scale=.25]
            \draw [fill=black] (-2,0) rectangle (-1,1) (-1.5,0) node[below] {\tiny\rotatebox{-90}{\texttt{\textbf{Cochez le nom}}}};''')
        with open('liste_eleves.csv') as g:
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
                write(r'''\draw[fill={color}] ({a},0) rectangle ({b},1) ({c},0) node[below]
                    {{\tiny \rotatebox{{-90}}{{\texttt{{{name}}}}}}};'''.format(**locals()))
        b += 1
        write(r'''\draw[rounded corners] (-3,2) rectangle ({b}, -6.5);
            \draw[] (-0.5,2) -- (-0.5,-6.5);
            \end{{tikzpicture}}
            \end{{center}}
            \vspace{{-1em}}

            '''.format(**locals()))
    except FileNotFoundError:
        print("Warning: liste_eleves.csv not found.")
        n_students = 0



    # Generate the table where students will answer.
    scale = CELL_SIZE_IN_CM
    write(r"""

        \simfill
        \vspace{{.5em}}

        \hfill\hfill
        {introduction}
        \begin{{tikzpicture}}[scale={scale}]
        \draw[fill=black] (-1,0) rectangle (0,1);
        """.format(**locals())
        )

    if isinstance(questions, int):
        questions = range(1, questions + 1)

    # Not all iterables have a .__len__() method, so calculate it.
    n_questions = 0

    for x1, name in enumerate(questions):
        x2=x1 + 1
        x3=.5*(x1 + x2)
        write(r"""\draw ({x1},0) rectangle ({x2},1) ({x3},0.5) node {{{name}}};
            """.format(**locals())
            )
        n_questions += 1

    if isinstance(answers, int):
        answers = ascii_letters[:answers]

    for i, name in enumerate(answers):
        y1 = -i
        y2 = y1 - 1
        y3 = .5*(y1 + y2)
        write(r"""
            \draw (-1,{y1}) rectangle (0,{y2}) (-0.5,{y3}) node {{{name}}};
            """.format(**locals())
            )
        for x1 in range(n_questions):
            opt = options.get((x1, i), "")
            x2=x1 + 1
            write(r"""\draw [{opt}] ({x1},{y1}) rectangle ({x2},{y2});
                """.format(**locals())
                )

    n_answers = i + 1

    write(r"""
\end{tikzpicture}
\hfill\hfill\hfil
""")


    config = {'n_questions': n_questions,
              'n_answers': n_answers,
              'n_students': n_students,
              }

    return content, config


def generate_body(text):
    content = []
    mode_mcq = False
    # A group of questions.
    group_opened = False
    question_opened = False
    for _line_ in text.split('\n'):
        line = _line_.lstrip()
        if not mode_qcm:
            if line.startswith('<') and not line.strip('< '):
                # Start of Multiple Choice Questions.
                mode_mcq = True
            else:
                content.append(_line_)
        else:
            if mode_mcq:
                if line.startswith('='):
                    if group_opened:
                        group_opened = False
                        content.append('#END')
                    title = line.strip('= ')
                    content.append('\subsection{%s}' % title)
                elif line.startswith('*'):
                    # Close last question before opening a new one.
                    if question_opened:
                        content.append('#END')
                    # Maybe this is the first question of the group.
                    if not group_opened:
                        group_opened = True
                        content.append('#SHUFFLE')
                    content.append('#ITEM')
                    content.append('#SHUFFLE')
                    question_opened = True

                elif line.startswith('-') or line.startswith('+'):
                    correct_answer = (line[0] == '+')
                    assert question_opened
                    content.append('#ITEM')
            if line.startswith('>') and not line.strip('> '):
                # End of Multiple Choice Questions.
                break
    if question_opened:
        content.append('#END')
    if group_opened:
        content.append('#END')
    return content



def generate_tex(text, filename=None, **kw):
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

    content, config = generate_header(**kw)
    content.extend(generate_body(text))
    content.append(r"\end{document}")
    # That's all folks !

    tex = ''.join(content)
    cfg = """# n_questions is the number of questions.
n_questions = {n_questions}
# n_answers is the number of answers per question.
n_answers = {n_answers}
# Length of students list (0 if no list at all)
n_students = {n_students}""".format(**config)

    # This is mostly for debuging...
    # ...to be removed later ?
    if filename is not None:
        with open("%s.tex" % filename, "w") as f:
            # Header
            f.write(tex)

        # Generate a config file:
        with open("%s.config" % filename, "w") as f:
            # Generate a config file:
            f.write(cfg)

    # Store the configuration at the end of the pTyX file.

    return tex
