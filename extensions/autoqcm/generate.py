from string import ascii_letters
import csv
import re
import sys
from os.path import join as abspath, dirname

script_path = dirname(abspath(sys._getframe().f_code.co_filename))
sys.path.insert(0, script_path)
from parameters import (SQUARE_SIZE_IN_CM, CELL_SIZE_IN_CM, MARGIN_LEFT_IN_CM,
                         MARGIN_RIGHT_IN_CM, PAPER_FORMAT, PAPER_FORMATS,
                         MARGIN_BOTTOM_IN_CM, MARGIN_TOP_IN_CM
                        )



class StaticStack():
    """This is a fixed values "stack".

    This "stack" is initialized with a tuple of successive values.
    Thoses values are accessible through `.level` attribute.

    One can only go up or down in the stack ; stack `.state` consist of all
    values below current position (values above are supposed not in the stack).
    We start at position 0.

    We can't go below first level, nor above last level.

    As a consequence, this "stack" can never be empty.

    >>> s = StaticStack(('a', 'b', 'c'))
    >>> s.levels
    ('a', 'b', 'c')
    >>> s.state
    ('a',)
    >>> s.up() # Return last top value.
    'a'
    >>> s.state
    ('a', 'b')
    >>> s.up()
    'b'
    >>> s.state
    ('a', 'b', 'c')
    >>> s.current
    'c'
    >>> s.up()
    IndexError: Can't go higher than c !
    >>> s.down()
    'c'
    >>> s.current
    'b'
    >>> 'c' in s
    False
    >>> s[-1]
    'b'
    >>> len(s)
    2
    >>> s.pos    # s[s.pos] == s[-1] == s.current is always True
    1
    >>> print(s)
    a, b (c)
    """

    def __init__(self, levels:tuple):
        self.__levels = levels
        self.__i = 0

    @property
    def levels(self):
        return self.__levels

    def up(self):
        "Go up in the stack and return previous level."
        if self.__i == len(self.__levels) - 1:
            raise IndexError("Can't go higher than %s !" % self.__levels[-1])
        self.__i += 1
        return self.__levels[self.__i - 1]

    def down(self):
        "Go down in the stack and return previous level."
        if self.__i == 0:
            raise IndexError("Can't go lower than %s !" % self.__levels[0])
        self.__i -= 1
        return self.__levels[self.__i + 1]

    @property
    def state(self):
        return self.__levels[:self.__i + 1]

    def __contains__(self, value):
        return value in self.state

    @property
    def pos(self):
        return self.__i

    def __len__(self):
        return self.__i + 1

    @property
    def current(self):
        return self.__levels[self.__i]

    def __getitem__(self, i):
        return self.state[i]

    def __str__(self):
        return ', '.join(str(v) for v in self.state) + \
                ' (%s)' % ', '.join(str(v) for v in self.levels[self.__i + 1:])





def generate_identification_band(identifier, full=True, squares_number=15):
    """Generate top banner of the page to be scanned later.

    `identifier` is the integer which identifies the sheet.

    - Generates two squares for calibration (top left and top right).
    - Generates an identification band so as to read automatically
      document number later.
    """
    content = []
    write = content.append

    s = SQUARE_SIZE_IN_CM
    if PAPER_FORMAT not in PAPER_FORMATS:
        raise ValueError('%s is not a valid paper format. \
                          Presently available formats are %s.'
                          % (PAPER_FORMAT, PAPER_FORMAT.keys()))
    # `w` is the page width left after removing borders (in cm).
    w = PAPER_FORMATS[PAPER_FORMAT][0] - MARGIN_LEFT_IN_CM - MARGIN_RIGHT_IN_CM
    # `l` is the length of the codebar (in cm).
    # (Add 2 to square_number since there is a first square always black for
    # detecting codebar, and a plain number written after code bar which is about
    # the same size as a square).
    l = (squares_number + 2)*s
    # The two top squares (at top left and top right corners) will be used
    # for calibration when scanning paper, since printer or scanner may rescale
    # or rotate content a bit.
    # The codebar, placed midway between them, will be used to read test number.
    write(r"\begin{tikzpicture}[every node/.style={inner sep=0,outer sep=0}]")

    if full:
        # Top left square.
        write(r"""\draw[fill=black] (0,0) rectangle ({s},{s});
            """.format(s=s))

    # Identification band
    x = (w - l)/2
    write(r"\draw[fill=black] (%s,0) rectangle (%s,%s);" % (x, x+s, s))
    n = identifier
    for i in range(squares_number):
        x += s
        color=("black" if n%2 else "white")
        write(r"\draw[fill=%s] (%s,0) rectangle (%s,%s);" % (color, x, x+s, s))
        n = n//2
    write(r"\draw (%s,%s) node [right] {\tiny{%s}};" % (x + 1.5*s, s/2, identifier))

    if full:
        # Top right square.
        write(r"\draw[fill=black] (%s,0) rectangle (%s,%s);" % (w-s, w, s))

    write("\end{tikzpicture}")

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
            \vspace{-1em}
            \begin{center}
            \begin{tikzpicture}[scale=.25]
            \draw [fill=black] (-2,0) rectangle (-1,1) (-1.5,0) node[below] {\tiny\rotatebox{-90}{\texttt{\textbf{Noircir la case}}}};''')
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



def generate_student_id_table(csv_path):
    """"Generate a table where the students can write its identification number.

    `csv_path` is the path of the CSV file who contains students names and ids.
    The first column of the CSV file must contain the ids.
    The table have a row for each digit, where the student check corresponding
    digit to indicate its number.
    """
    ids = {}
    # Read CSV file and generate the dictionary {id: "student name"}.
    with open(csv_path) as f:
        for row in csv.reader(f):
            n, *row = row
            ids[int(n)] = ' '.join(item.strip() for item in row)
    digits = len(str(max(ids)))
    content = []
    write = content.append
    write('\n\n')
    write(r'Votre numéro~:\quad\begin{tikzpicture}[baseline=-10pt,scale=.25]')
    write(r'\draw[fill=black] (-1, 0) rectangle (0,%s);' % (-digits))
    # One column for each possibility (0-9).
    for i in range(10):
        # Digit above each column.
        write(r'\draw (%s,0.5) node {\small %s};' %(i + .5, i))
        # One row for each digit of the student id number.
        for j in range(digits):
            write('r\draw (%s,%s) rectangle (%s,%s);' % (i, -j, i+1, -j-1))
    write(r'\end{tikzpicture}')
    write(r'\qquad')
    write(r'Nom~:~\dotfill')
    write(r'Prénom~:~\dotfill')
    write(r'Groupe~:~\dots')
    write('\n\n')
    return '\n'.join(content), ids



def generate_table_for_answers(questions, answers, correct_answers=(), flip=False, options={}):
    """Generate the table where students select correct answers.

    `questions` is either a list (or any iterable) of questions numbers,
    or an integer n (questions number will be automatically generated then:
    1, 2, 3, ..., n).

    `answers` is either a list (or any iterable) of questions numbers,
    or an integer n≤26 (answers identifiers will be automatically generated then:
    a, b, c, ...).

    `correct_answers` is a list of correct answers for each questions (so,
    it's a list of lists of integers).
    For example, `[[0, 2], [3], []]` means that the correct answers for question 1
    were the answers number 1 and 3 (`[0, 2]`), while the only correct answer for question 2
    was number 4 (`[3]`) and question 3 had no correct answer at all (`[]`).

    If `flip` is True, rows and columns will be inverted. This may gain some place
    if there are more answers per question than questions.

    `options` is a dict whom keys are tuples (line, column) and values are tikz options
    to be passed to corresponding cell in the table for answers.
    """
    content = []
    write = content.append

    # Generate the table where students will answer.
    tkzoptions = ['scale=%s' % CELL_SIZE_IN_CM]
    if flip:
        tkzoptions.extend(['x={(0cm,-1cm)}', 'y={(-1cm,0cm)}'])

    write(r"""
        \begin{tikzpicture}[%s]
        \draw[thin,fill=black] (-1,0) rectangle (0,1);""" % (','.join(tkzoptions)))

    if isinstance(questions, int):
        assert questions > 0
        questions = range(1, questions + 1)

    # Not all iterables have a .__len__() method, so calculate it.
    n_questions = 0

    for x1, name in enumerate(questions):
        x2=x1 + 1
        x3=.5*(x1 + x2)
        write(r"""\draw[ultra thin] ({x1},0) rectangle ({x2},1) ({x3},0.5) node {{{name}}};""".format(**locals()))
        n_questions += 1

    if isinstance(answers, int):
        assert answers > 0
        answers = ascii_letters[:answers]

    i = -1
    for i, name in enumerate(answers):
        y1 = -i
        y2 = y1 - 1
        y3 = .5*(y1 + y2)
        write(r"""
            \draw[ultra thin] (-1,{y1}) rectangle (0,{y2}) (-0.5,{y3}) node {{{name}}};""".format(**locals()))
        for j in range(n_questions):
            opt = options.get((i, j), "")
            x1 = j
            x2 = x1 + 1
            if j < len(correct_answers):
                if i in correct_answers[j]:
                    opt = 'fill=gray,' + opt
            write(r"""\draw [ultra thin,{opt}] ({x1},{y1}) rectangle ({x2},{y2});""".format(**locals()))

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



def generate_latex_header():
    paper_format = '%spaper' % PAPER_FORMAT.lower()
    # LaTeX header is in two part, so as user may insert some customization here.
    return [r"""\documentclass[{paper_format},10pt]{{article}}
    \PassOptionsToPackage{{utf8}}{{inputenc}}
    \PassOptionsToPackage{{document}}{{ragged2e}}
    \PassOptionsToPackage{{left={left}cm,right={right}cm,top={top}cm,bottom={bottom}cm}}{{geometry}}
    \parindent=0cm
    \newcommand*\graysquared[1]{{\tikz[baseline=(char.base)]{{
        \node[fill=gray,shape=rectangle,draw,inner sep=2pt] (char) {{\color{{white}}\textbf{{#1}}}};}}}}
    \newcommand*\whitesquared[1]{{\tikz[baseline=(char.base)]{{
        \node[fill=white,shape=rectangle,draw,inner sep=2pt] (char) {{\color{{black}}\textbf{{#1}}}};}}}}
    \newcommand*\AutoQCMcircled[1]{{\tikz[baseline=(char.base)]{{
        \node[shape=circle,fill=blue!20!white,draw,inner sep=2pt] (char) {{\textbf{{#1}}}};}}}}
    \makeatletter
    \newcommand{{\AutoQCMsimfill}}{{%
    \leavevmode \cleaders \hb@xt@ .50em{{\hss $\sim$\hss }}\hfill \kern \z@
    }}
    \makeatother
    \newcounter{{answerNumber}}
    \renewcommand{{\thesubsection}}{{\Alph{{subsection}}}}
    """.format(paper_format=paper_format, left=MARGIN_LEFT_IN_CM,
                           right=MARGIN_RIGHT_IN_CM,
                           top=MARGIN_TOP_IN_CM, bottom=MARGIN_BOTTOM_IN_CM),
    # Custom packages will be loaded here
    r"""\usepackage{inputenc}
    \usepackage{ragged2e}
    \usepackage{geometry}
    \usepackage{pifont}
    \usepackage{textcomp}
    \usepackage{nopageno}
    \usepackage{tikz}
    \usepackage{enumitem} % To resume an enumeration.
    \setenumerate[0]{label=\protect\AutoQCMcircled{\arabic*}}
    """]



def generate_answers_and_score(config, name, identifier, score, max_score):
    "Generate plain LaTeX code corresponding to score and correct answers."
    t = generate_table_for_answers(config['questions'], config['answers (max)'],
             correct_answers=config['answers'][identifier], flip=config['flip'])
    left = MARGIN_LEFT_IN_CM
    right = MARGIN_RIGHT_IN_CM
    top = MARGIN_TOP_IN_CM
    bottom = MARGIN_BOTTOM_IN_CM
    return (r"""
    \documentclass[{paper_format},10pt]{article}
    \usepackage[utf8]{inputenc}
    \usepackage[document]{ragged2e}
    \usepackage{nopageno}
    \usepackage{tikz}
    \usepackage[left=%(left)scm,right=%(right)scm,top=%(top)scm,bottom=%(bottom)scm]{geometry}
    \parindent=0cm
    \usepackage{textcomp}

    \begin{document}
    \begin{Large}\textsc{%(name)s}\end{Large}
    \hfill\begin{tikzpicture}
    \node[draw,very thick,rectangle, rounded corners,red!70!black] (0,0) {
    \begin{Large}
    Score~: %(score)s/%(max_score)s
    \end{Large}};
    \end{tikzpicture}

    \bigskip

    Solution~:
    \medskip

    %(t)s

    \end{document}
    """ % locals())







def generate_tex(text):

    #TODO: improve ability to customize this part ?

    code = []

    levels = ('ROOT', 'QCM', 'SECTION', 'QUESTION_BLOCK', 'ANSWERS')
    stack = StaticStack(levels)

    def begin(level, **kw):

        # Keep track of previous level: this is useful to know if a question block
        # is the first of a section, for example.
        previous_level = stack.current
        # First, close any opened level until founding a parent.
        close(level)

        if level == 'QCM':
            code.append('#QCM')
            code.append('#SHUFFLE % (sections)')

        elif level == 'SECTION':
            code.append('#ITEM % shuffle sections')
            if 'title' in kw:
                code.append(r'\section{%s}' % kw['title'])

        elif level == 'QUESTION_BLOCK':
            if stack.current == 'QCM':
                begin('SECTION')

            if previous_level in ('SECTION', 'QCM'):
                # This is the first question block.
                # NB: \begin{enumerate} must not be written just after the begining
                # of the section, since there may be some explanations between
                # the section title and the first question.
                code.append('\\begin{enumerate}[resume]')
                code.append('#SHUFFLE % (questions)')
            #~ # Open a section to add a \\begin{enumerate} only once.
            #~ if stack[-1] != 'SECTION':
                #~ begin('SECTION')
            # Question blocks are shuffled. As an exception, a block starting
            # with '>' must not be separated from previous block.
            if kw.get('shuffle', True):
                code.append('#ITEM % shuffle questions') # shuffle blocks.
            code.append('\\item')
            code.append('\\setcounter{answerNumber}{0}')
            code.append('#PICK % (question)')

        elif level == 'ANSWERS':
            # First, end question.
            code.append('#END % question')
            # Shuffle answers.
            code.append('#ANSWERS_BLOCK')
            code.append('#SHUFFLE % (answers)')

        else:
            raise RuntimeError('Unknown level: %s' % level)

        #~ elif tag == 'NEW_QUESTION':
            #~ stack.append(
            #~ code.append('#NEW_QUESTION')
            #~ answer_number = 0

        print(stack.pos*4*' ' + 'begin %s' % level)
        stack.up()
        assert stack.current == level

        #~ if tag == 'QUESTION_BLOCK':
            #~ begin('NEW_QUESTION')

    def close(level):
        """Close `level` (and any opened upper one).

        For example, close('SECTION') will close levels until returning
        to a level lower than SECTION ('ROOT' or 'QCM').
        Any opened upper level ('QUESTION_BLOCK' or 'ANSWERS') will be closed first.
        """

        while level in stack:
            # Note that close('ROOT') will raise an error, as expected.
            _level = stack.down()
            print(stack.pos*4*' ' + 'close %s' % _level)
            #~ print('Current code: %s' % repr(code[-20:]))

            # Specify how to close each level.
            if _level == 'QCM':
                code.append('#END_SHUFFLE % (sections)')
                code.append('#END_QCM')

            elif _level == 'SECTION':
                code.append('#END_SHUFFLE % (questions)')
                code.append(r'\end{enumerate}')

            elif _level == 'QUESTION_BLOCK':
                code.append('#END_PICK % (question)')

            elif _level == 'ANSWERS':
                # Remove  blank lines which may be placed between two answers
                # when shuffling.
                while code[-1].strip() == '':
                    code.pop()
                code.append('#END_SHUFFLE % (answers)')
                code.append('#END % (answers block)')



    previous_line = None
    before_QCM = True
    is_header = False
    header = ['#QCM_HEADER{']

    intro = ['#ASK_ONLY % (introduction)']
    # The table that students use to answer MCQ will be generated and inserted here by default.
    # (User can customize its position by using #TABLE_FOR_ANSWERS tag).
    if '#TABLE_FOR_ANSWERS' not in text:
        intro.append('#TABLE_FOR_ANSWERS')

    for _line_ in text.split('\n'):
        line = _line_.strip()
        n = len(line)

        if n >= 3 and all(c == '<' for c in line):  # <<<
            # start MCQ
            header.append('}')
            code.extend(header)

            intro.append('#END % (introduction)')
            code.extend(intro)
            print('Parsing QCM...\n')
            print('STRUCTURE:\n')
            begin('QCM')
            before_QCM = False

        elif before_QCM:
            if n >= 3 and all(c == '=' for c in line):  # ===
                # Enter (or leave) header section.
                is_header = not is_header
            elif is_header:
                header.append(_line_)
            else:
                intro.append(_line_)

        elif n >= 3 and line.startswith('=') and line.endswith('='):
            # === title ===
            # Start a new section.
            begin('SECTION', title=line.strip('= '))

        elif any(line.startswith(s) for s in ('* ', '> ', 'OR ')):
            # * question
            # Start a question block, with possibly several versions of a question.

            if line[:2] == 'OR':
                # If line starts with 'OR', this is not a new block, only another
                # version of current question block.
                close('ANSWERS')
            else:
                # This is a new question.
                begin('QUESTION_BLOCK', shuffle=(line[0]=='*'))
            code.append('#ITEM % pick a version') # pick a block.

            code.append('#NEW_QUESTION')
            code.append(line[2:])

        elif line.startswith('#L_ANSWERS{'):
            # End question.
            # (Usually, questions are closed when seeing answers, ie. lines
            # introduced by '-' or '+').
            code.append('#END % question (before l_answers)')
            code.append(line)

        elif line.startswith('- ') or line.startswith('+ '):
            # - incorrect answer
            # + correct answer

            assert stack.current in ('ANSWERS', 'QUESTION_BLOCK')

            if stack.current == 'QUESTION_BLOCK':
                # This is the first answer of a new answer block.
                begin('ANSWERS')

            elif previous_line == '':
                # A blank line may be used to separate answers groups.
                # (It should not appear in final pdf, so overwrite it).
                # (NB: This must not be done for the first answer !)
                code[-1] = '#END_SHUFFLE % (answers)'
                code.append('#SHUFFLE % (answers)')

            code.append('#ITEM % shuffling answers')
            iscorrect = (line[0] == '+')
            code.append('#NEW_ANSWER{%s}' % iscorrect)

            code.append('#PROPOSED_ANSWER %s#END' % line[2:])

        elif n >= 3 and all(c == '>' for c in line):  # >>>
            # End MCQ
            close('QCM')

        else:
            code.append(_line_)

        previous_line = line

    code.append(r'\end{document}')
    return '\n'.join(code)



