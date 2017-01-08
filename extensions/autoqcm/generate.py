from string import ascii_letters
import csv
import re

from .parameters import SQUARE_SIZE_IN_CM, CELL_SIZE_IN_CM



def generate_identification_band(identifier, full=True):
    """Generate top banner of the page to be scanned later.

    `identifier` is the integer which identifies the sheet.

    - Generates two squares for calibration (top left and top right).
    - Generates an identification band so as to read automatically
      document number later.
    """
    content = []
    write = content.append

    # Two top squares to calibrate and identification band between them

    if full:
        # Top left and top right squares.
        write(r"""\begin{{tikzpicture}}[scale={scale}]
            \draw[fill=black] (0,0) rectangle (1,1);
            \draw[fill=black] (\linewidth/{scale}-28.45274,0) rectangle (\linewidth/{scale},1);
            \end{{tikzpicture}}
            \vspace{{-{scale}cm}}

            """.format(scale=SQUARE_SIZE_IN_CM))

    # Identification band
    write(r"""\hfill
        \begin{{tikzpicture}}[scale={scale}]
        \draw[fill=black] (-1,0) rectangle (0,1);

        """.format(scale=SQUARE_SIZE_IN_CM))

    n = identifier
    for i in range(15):
        write(r"""\draw[fill={color}] ({x1},0) rectangle ({x2},1);
            """.format(color=("black" if n%2 else "white"), x1=i, x2=i+1))
        n = n//2

    write(r"""\draw (15, .5) node [right] {{\tiny{identifier}}};
        \end{{tikzpicture}}
        \hfill\hfil""".format(**locals()))

    #~ # Top right square.
    #~ write(r"""\begin{{tikzpicture}}[scale={scale}]

        #~ \end{{tikzpicture}}
        #~ """.format(scale=SQUARE_SIZE_IN_CM))

    # Header delimiter.

    if full:
        write(r"""
        \vspace{-.5em}
        \begin{scriptsize}\hfill\textsc{Ne rien écrire ci-dessus.}\hfill\hfill\hfill\textsc{Ne rien écrire ci-dessus.}\hfill\hfil\end{scriptsize}
        """)
    return '\n'.join(content)



def generate_students_list(csv_path='', _n_student=None):
    """Generate a list of all students, where student can check his name.

    `csv_path` is the path of the CSV file who contains students names.
    `_n_student` is used to prefilled the table (for debuging).
    """
    students = []
    if not csv_path:
        return '', []
    try:
        content = []
        content.append(r'''
            #ASK_ONLY
            \vspace{-1em}
            \begin{center}
            \begin{tikzpicture}[scale=.25]
            \draw [fill=black] (-2,0) rectangle (-1,1) (-1.5,0) node[below] {\tiny\rotatebox{-90}{\texttt{\textbf{Cochez le nom}}}};''')
        # Read CSV file and generate list of students name.
        with open(csv_path) as f:
            for row in csv.reader(f):
                name = ' '.join(item.strip() for item in row)
                students.append(name)

        # Generate the corresponding names table in LaTeX.
        for i, name in enumerate(reversed(students)):
            # Troncate long names.
            if len(name) >= 15:
                _name = name[:13].strip()
                if " " not in name[12:13]:
                    _name += "."
                name = _name
            a = 2*i
            b = a + 1
            c = a + 0.5
            color = ('black' if _n_student == len(students) - i else 'white')
            content.append(r'''\draw[fill={color}] ({a},0) rectangle ({b},1) ({c},0) node[below]
                {{\tiny \rotatebox{{-90}}{{\texttt{{{name}}}}}}};'''.format(**locals()))
        b += 1
        content.append(r'''\draw[rounded corners] (-3,2) rectangle ({b}, -6.5);
            \draw[] (-0.5,2) -- (-0.5,-6.5);
            \end{{tikzpicture}}
            \end{{center}}
            #END
            \vspace{{-1em}}
            '''.format(**locals()))
    except FileNotFoundError:
        print("Warning: `%s` not found." % csv_path)
        return '', []
    return '\n'.join(content), students



def generate_students_list(csv_path='', _n_student=None):
    """Generate a list of all students, where student can check his name.

    `csv_path` is the path of the CSV file who contains students names.
    `_n_student` is used to prefilled the table (for debuging).
    """
    students = []
    if not csv_path:
        return '', []
    try:
        content = []
        content.append(r'''
            \vspace{-1em}
            \begin{center}
            \begin{tikzpicture}[scale=.25]
            \draw [fill=black] (-2,0) rectangle (-1,1) (-1.5,0) node[below] {\tiny\rotatebox{-90}{\texttt{\textbf{Cochez le nom}}}};''')
        # Read CSV file and generate list of students name.
        with open(csv_path) as f:
            for row in csv.reader(f):
                name = ' '.join(item.strip() for item in row)
                students.append(name)

        # Generate the corresponding names table in LaTeX.
        for i, name in enumerate(reversed(students)):
            # Troncate long names.
            if len(name) >= 15:
                _name = name[:13].strip()
                if " " not in name[12:13]:
                    _name += "."
                name = _name
            a = 2*i
            b = a + 1
            c = a + 0.5
            color = ('black' if _n_student == len(students) - i else 'white')
            content.append(r'''\draw[fill={color}] ({a},0) rectangle ({b},1) ({c},0) node[below]
                {{\tiny \rotatebox{{-90}}{{\texttt{{{name}}}}}}};'''.format(**locals()))
        b += 1
        content.append(r'''\draw[rounded corners] (-3,2) rectangle ({b}, -6.5);
            \draw[] (-0.5,2) -- (-0.5,-6.5);
            \end{{tikzpicture}}
            \end{{center}}
            \vspace{{-1em}}
            '''.format(**locals()))
    except FileNotFoundError:
        print("Warning: `%s` not found." % csv_path)
        return '', []
    return '\n'.join(content), students



def generate_table_for_answers(questions, answers, introduction='', options={}):
    """Generate the table where students select correct answers.

    `questions` is either a list (or any iterable) of questions numbers,
    or an integer n (questions number will be automatically generated then:
    1, 2, 3, ..., n).

    `answers` is either a list (or any iterable) of questions numbers,
    or an integer n≤26 (answers identifiers will be automatically generated then:
    a, b, c, ...).

    `options` is a dict whom keys are tuples (column, line) and values are tikz options
    to be passed to corresponding cell in the table for answers.
    """
    content = []
    write = content.append

    # Generate the table where students will answer.
    scale = CELL_SIZE_IN_CM
    write(r"""
        \vspace{{.5em}}

        {introduction}

        \begin{{tikzpicture}}[scale={scale}]
        \draw[thin,fill=black] (-1,0) rectangle (0,1);""".format(**locals()))

    if isinstance(questions, int):
        questions = range(1, questions + 1)

    # Not all iterables have a .__len__() method, so calculate it.
    n_questions = 0

    for x1, name in enumerate(questions):
        x2=x1 + 1
        x3=.5*(x1 + x2)
        write(r"""\draw[ultra thin] ({x1},0) rectangle ({x2},1) ({x3},0.5) node {{{name}}};""".format(**locals()))
        n_questions += 1

    if isinstance(answers, int):
        answers = ascii_letters[:answers]

    for i, name in enumerate(answers):
        y1 = -i
        y2 = y1 - 1
        y3 = .5*(y1 + y2)
        write(r"""
            \draw[ultra thin] (-1,{y1}) rectangle (0,{y2}) (-0.5,{y3}) node {{{name}}};""".format(**locals()))
        for x1 in range(n_questions):
            opt = options.get((x1, i), "")
            x2=x1 + 1
            write(r"""\draw [ultra thin,#GRAY_IF_CORRECT{{{x1}}}{{{i}}}{opt}] ({x1},{y1}) rectangle ({x2},{y2});""".format(**locals()))

    n_answers = i + 1

    write(r'''\draw [thick] (-1,1) rectangle ({x2},{y2});
              %\draw [thick] (-1,0) -- ({x2},0);
              '''.format(**locals()))

    for i in range(0, x2):
        write(r'''\draw [thick] ({i},1) -- ({i},{y2});
              '''.format(**locals()))

    write(r"""\end{tikzpicture}\hfill\hfill\hfil
        """)

    return '\n'.join(content)





def generate_tex(text):
    #TODO: add ability to customize this part ?
    content = [r"""\documentclass[a4paper,10pt]{article}""",
        "<--Customized header-->",
        r"""\usepackage[utf8]{inputenc}
        \usepackage[document]{ragged2e}
        \usepackage{nopageno}
        \usepackage{tikz}
        \usepackage[left=1cm,right=1cm,top=1cm,bottom=1cm]{geometry}
        \parindent=0cm
        \usepackage{pifont}
        \usepackage{textcomp}
        \usepackage{enumitem} % To resume an enumeration.
        \newcommand*\graysquared[1]{\tikz[baseline=(char.base)]{
            \node[fill=gray,shape=rectangle,draw,inner sep=2pt] (char) {\color{white}\textbf{#1}};}}
        \newcommand*\whitesquared[1]{\tikz[baseline=(char.base)]{
            \node[fill=white,shape=rectangle,draw,inner sep=2pt] (char) {\color{black}\textbf{#1}};}}
        \newcommand*\AutoQCMcircled[1]{\tikz[baseline=(char.base)]{
            \node[shape=circle,fill=blue!20!white,draw,inner sep=2pt] (char) {\textbf{#1}};}}
        \makeatletter
        \newcommand{\AutoQCMsimfill}{%
        \leavevmode \cleaders \hb@xt@ .50em{\hss $\sim$\hss }\hfill \kern \z@
        }
        \makeatother
        \newcounter{answerNumber}
        \renewcommand{\thesubsection}{\Alph{subsection}}
        \setenumerate[0]{label=\protect\AutoQCMcircled{\arabic*}}
        \begin{document}"""]

    content.append("#AUTOQCM_BARCODE")

    # Extract from text the path of the csv file containing students names.
    m=re.match("[ ]*%[ ]*csv:(.*)", text, re.IGNORECASE)
    if m:
        csv_path = m.group(1).strip()
        code, students_list = generate_students_list(csv_path)
        content.append('#ASK_ONLY')
        content.append(code)
        content.append('#END')
    else:
        print("Warning: no student list provided (or incorrect syntax), ignoring...")

    content.append("#IF{'AUTOQCM__SCORE_FOR_THIS_STUDENT' in dir()}")
    content.append(r"""
        \begin{Large}\textsc{#{AUTOQCM__STUDENT_NAME}}\end{Large}

        \hfill\begin{tikzpicture}
        \node[draw,very thick,rectangle, rounded corners,red!70!black] (0,0) {
        \begin{Large}
        Score~: #{AUTOQCM__SCORE_FOR_THIS_STUDENT}/#{AUTOQCM__MAX_SCORE}
        \end{Large}};
        \end{tikzpicture}

        Solution~:
        \medskip
        """)
    content.append('#ELSE')
    content.append(r'\AutoQCMsimfill')
    content.append('#END')

    content.append('<--Table for answers-->') # To be filled later with table for answers.
    # (Dimensions are not known for now.)

    # Number of questions
    question_number = 0
    # Number of answers per question
    # If the number of answers is not the same for all questions,
    # then the max will be returned.
    n_answers = 0
    answer_number = 0
    # Set all flags to False before parsing.
    mode_qcm = group_opened = question_opened = has_groups = has_qcm = header_closed = False

    lastline = None

    content.append("#IF{'AUTOQCM__SCORE_FOR_THIS_STUDENT' not in dir()}")

    intro = ['#ASK_ONLY']
    header=[]

    for _line_ in text.split('\n'):
        line = _line_.lstrip()
        if not header_closed:
            if re.search('#LOAD{[ ]*autoqcm[ ]*}', line):
                header_closed = True
            else:
                header.append(_line_)
        elif not mode_qcm:
            # -------------------- STARTING QCM ------------------------
            if line.startswith('<<') and not line.strip('< '):
                # Close introduction.
                intro.append('#END')
                # Start of Multiple Choice Questions.
                mode_qcm = has_qcm = True
                # Shuffles QCM sections.
                content.append('#NEW_QCM')
            elif has_qcm:
                content.append(_line_)
            else:
                # Some indications for students before QCM.
                intro.append(_line_)
        else:
            # -------------------- PARSING QCM -------------------------
            if line.startswith('='):
                # Starts a group of questions.
                # By default, questions inside a group are shuffled,
                # and groups are printed in random order.

                if not has_groups:
                    # This is the first group encountered.
                    # Shuffle groups.
                    content.append('#SHUFFLE')
                has_groups = True

                # First, close previous group (if any).
                if group_opened:
                    if question_opened:
                        # Remove any previous blank lines.
                        # This avoid blank lines beeing inserted between
                        # two consecutive answers when shuffling answers.
                        while content[-1].strip() == '':
                            content.pop()
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
                # Close last question before opening a new one.
                if question_opened:
                    # Remove any previous blank lines.
                    # This avoid blank lines beeing inserted between
                    # two consecutive answers when shuffling answers.
                    while content[-1].strip() == '':
                        content.pop()
                    content.append('#END')
                # Maybe this is the first question of the group.
                if not group_opened:
                    group_opened = True
                    content.append('\\begin{enumerate}[resume]')
                    # Shuffle questions.
                    content.append('#SHUFFLE')
                if line[0] == '*':
                    # (If line starts with '>', question must follow
                    # the last one.)
                    content.append('#ITEM')
                content.append('\\item')
                content.append('\\setcounter{answerNumber}{0}')
                content.append('#NEW_QUESTION %s#END' % line[2:])
                # Shuffle answers.
                content.append('#SHUFFLE')
                question_opened = True

            elif line.startswith('- ') or line.startswith('+ '):
                if answer_number == 0:
                    #content.append('\n\n')
                    content.append('\n\n\\sloppy')
                elif lastline == '':
                    # A blank line may be used to separate answers groups.
                    # (It should not appear in final pdf, so overwrite it).
                    content[-1] = '#END'
                    content.append('#SHUFFLE')
                answer_number += 1
                assert question_opened
                content.append('#ITEM%')
                iscorrect = (line[0] == '+')
                content.append('#NEW_ANSWER{%s}' % iscorrect + '%')
                # Add counter for each answer.
                #char = chr(96 + answer_number)
                content.append('\\stepcounter{answerNumber}%')
                # When the pdf with solutions will be generated, incorrect answers
                # will be preceded by a white square, while correct ones will
                # be preceded by a gray one.
                if iscorrect:
                    command = '\\graysquared'
                else:
                    command = '#QUESTION{\\graysquared}#ANSWER{\\whitesquared}'
                content.append('%s{\\alph{answerNumber}}~~\\mbox{#PROPOSED_ANSWER %s#END}\\qquad\\linebreak[3]' % (command, line[2:]) + '%')


            # -------------------- ENDING QCM --------------------------
            elif line.startswith('>>') and not line.strip('> '):
                # End of Multiple Choice Questions.
                mode_qcm = False
                # Ending last group...
                if group_opened:
                    if question_opened:
                        # Remove any previous blank lines.
                        # This avoid blank lines beeing inserted between
                        # two consecutive answers when shuffling answers.
                        while content[-1].strip() == '':
                            content.pop()
                        content.append('#END')
                        #content.append('\\fussy')
                        question_opened = False
                    # End last group of questions.
                        content.append('#END')
                    group_opened = False
                    content.append('\\end{enumerate}')
                # Ending QCM sections shuffling...
                if has_groups:
                    content.append('#END')
                has_groups = False
                content.append('#END_QCM')
                # ... bye bye !
            # ----------------------------------------------------------

            else:
                content.append(_line_)
        lastline = line

    n_answers = max(n_answers, answer_number)
    if question_opened:
        content.append('#END')
    if group_opened:
        content.append('#END')
    i = content.index('<--Table for answers-->')
    content[i] = generate_table_for_answers(question_number, n_answers, introduction='\n'.join(intro))
    i = content.index('<--Customized header-->')
    content[i] = '\n'.join(header)
    # This '#END' refer to '#IF{'AUTOQCM__SCORE_FOR_THIS_STUDENT' in dir()}'.
    content.append('#END')
    content.append(r"\end{document}")
    return '\n'.join(content), students_list, question_number, n_answers



