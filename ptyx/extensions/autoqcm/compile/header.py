from string import ascii_letters
import csv
#import sys
from os.path import abspath, dirname, isabs, join, expanduser

#script_path = dirname(abspath(sys._getframe().f_code.co_filename))
#sys.path.insert(0, script_path)
from ..parameters import (CELL_SIZE_IN_CM, MARGIN_LEFT_IN_CM, # SQUARE_SIZE_IN_CM,
                         MARGIN_RIGHT_IN_CM, PAPER_FORMAT, # PAPER_FORMATS,
                         MARGIN_BOTTOM_IN_CM, MARGIN_TOP_IN_CM,
                         CALIBRATION_SQUARE_POSITION,
                         CALIBRATION_SQUARE_SIZE
                        )
from ..tools.config_parser import correct_answers


class IdentifiantError(RuntimeError):
    pass

def _byte_as_codebar(byte, n=0):
    '''Generate LaTeX code (TikZ) for byte number `n` in ID band.

    - `byte` is a number between 0 and 255, or LaTeX code resulting
      in such a number.
      If the number is above 255, encoding will be wrong.
    - `n` should be incremented at each call, so as not to overwrite
      a previous codebar.
    '''
    return fr"""
    \n={byte};
    \j={n};
    for \i in {{1,...,8}}{{%
            \r = int(Mod(\n,2));
            \n = int(\n/2);
            {{\draw[fill=color\r] ({{\i*0.25+2*\j}},0) rectangle ({{\i*0.25+0.25+2*\j}},0.25);
             }};
            }};"""


def ID_band(ID, calibration=True):
    """Generate top banner of the page to be scanned later.

    `ID` is the integer which identifies a test, each test being different.

    This top banner is made of:
    - four squares for calibration (top left, top right,
      bottom left, bottom right, at 1 cm of the border).
      If `calibration` is False, those squares are not displayed.

    - an identification band (kind of codebar) midway between
      the top squares.
      This ID band is used to encode both the MCQ ID number and the page
      number. They will be read automatically later.

    NB:
    - There is no need to provide the page number, since it will be
      handled directly by LaTeX.
    - Page number above 255 will result in incorrect encoding
      (256 will be encoded as 0).
    """

    l = [r"""\newcommand\CustomHeader{%
    \begin{tikzpicture}[remember picture,overlay,
                    every node/.style={inner sep=0,outer sep=-0.2}]"""]
    if calibration:
        pos = CALIBRATION_SQUARE_POSITION
        pos2 = CALIBRATION_SQUARE_POSITION + CALIBRATION_SQUARE_SIZE
        l.append(fr"""
        \draw[fill=black] ([xshift={pos}cm,yshift=-{pos}cm]current page.north west)
            rectangle ([xshift={pos2}cm,yshift=-{pos2}cm]current page.north west);
        \draw[fill=black] ([xshift=-{pos}cm,yshift=-{pos}cm]current page.north east)
            rectangle ([xshift=-{pos2}cm,yshift=-{pos2}cm]current page.north east);
        \draw[fill=black] ([xshift={pos}cm,yshift={pos}cm]current page.south west)
            rectangle ([xshift={pos2}cm,yshift={pos2}cm]current page.south west);
        \draw[fill=black] ([xshift=-{pos}cm,yshift={pos}cm]current page.south east)
            rectangle ([xshift=-{pos2}cm,yshift={pos2}cm]current page.south east);""")
        # ~ l.append(r"""
        # ~ \draw[fill=black] ([xshift=1cm,yshift=-1cm]current page.north west)
            # ~ node {\zsavepos{top-left}} rectangle ([xshift=1.25cm,yshift=-1.25cm]current page.north west);
        # ~ \draw[fill=black] ([xshift=-1cm,yshift=-1cm]current page.north east)
         # ~ node {\zsavepos{top-right}}
            # ~ rectangle ([xshift=-1.25cm,yshift=-1.25cm]current page.north east);
        # ~ \draw[fill=black] ([xshift=1cm,yshift=1cm]current page.south west)
          # ~ node {\zsavepos{bottom-left}}
             # ~ rectangle ([xshift=1.25cm,yshift=1.25cm]current page.south west);
        # ~ \draw[fill=black] ([xshift=-1cm,yshift=1cm]current page.south east)
          # ~ node {\zsavepos{bottom-right}}
             # ~ rectangle ([xshift=-1.25cm,yshift=1.25cm]current page.south east);""")
    l.append(r"""\node at ([yshift=-1cm]current page.north) [anchor=north] {
            \begin{tikzpicture}
            \definecolor{color0}{rgb}{1,1,1}
            \definecolor{color1}{rgb}{0,0,0}
            \draw[fill=black] (0,0) rectangle (0.25,0.25);
            \tikzmath {""")
    l.append(_byte_as_codebar(r'\thepage'))
    l.append(_byte_as_codebar(ID%256, n=1))
    l.append(_byte_as_codebar(ID//256, n=2))
    l.append(fr"""}}
        \node[anchor=west] at  ({{2.5+2*\j}},0.1)
            {{\scriptsize\textbf{{\#{ID}}}~:~{{\thepage}}/\zpageref{{LastPage}}}};
        \end{{tikzpicture}}}};

        \draw[dotted]  ([xshift=-1cm,yshift=-2cm]current page.north east)
            -- ([xshift=1cm,yshift=-2cm]current page.north west)
            node [pos=0.25,fill=white]
            {{\,\,\scriptsize\textuparrow\,\,\textsc{{N'écrivez rien au
            dessus de cette ligne}}\,\,\textuparrow\,\,}}
            node [pos=0.75,fill=white]
            {{\,\,\scriptsize\textuparrow\,\,\textsc{{N'écrivez rien au
            dessus de cette ligne}}\,\,\textuparrow\,\,}};
    \end{{tikzpicture}}}}""")
    # ~ l.append('\n')
    # ~ for y in ('top', 'bottom'):
        # ~ for x in ('left', 'right'):
            # ~ pos = f'{y}-{x}'
            # ~ l.append(fr'\write\mywrite{{{pos}: '
                    # ~ fr'(\dimtomm{{\zposx{{{pos}}}sp}}, '
                    # ~ fr'\dimtomm{{\zposy{{{pos}}}sp}})}}')
    # ~ l.append('\n')
    return ''.join(l)



def extract_ID_NAME_from_csv(csv_path, script_path):
    """`csv_path` is the path of the CSV file who contains students names and ids.
    The first column of the CSV file must contain the ids.

    Return a dictionnary containing the students ID and corresponding names.
    """
    csv_path = expanduser(csv_path)
    if not isabs(csv_path):
        csv_path = abspath(join(dirname(script_path), csv_path))
    # XXX: support ODS and XLS files ?
    # soffice --convert-to cvs filename.ods
    # https://ask.libreoffice.org/en/question/2641/convert-to-command-line-parameter/
    ids = {}
    # Read CSV file and generate the dictionary {id: "student name"}.
    with open(csv_path) as f:
        dialect = csv.Sniffer().sniff(f.read(1024))
        f.seek(0)
        for row in csv.reader(f, dialect):
            n, *row = row
            ids[n.strip()] = ' '.join(item.strip() for item in row)
    return ids


def extract_NAME_from_csv(csv_path, script_path):
    """`csv_path` is the path of the CSV file who contains students names.

    Return a list of students names.
    """
    if not isabs(csv_path):
        csv_path = abspath(join(dirname(script_path), csv_path))

    names = []
    # Read CSV file and generate the dictionary {id: "student name"}.
    with open(csv_path) as f:
        for row in csv.reader(f):
            names.append(' '.join(item.strip() for item in row))
    return names


def students_checkboxes(names, _n_student=None):
    """Generate a list of all students, where student can check his name.

    `names` is a list of students names.
    `_n_student` is used to prefilled the table (for debuging).
    """
    content = [r'''
        \vspace{-1em}
        \begin{center}
        \begin{tikzpicture}[scale=.25]
        \draw [fill=black] (-2,0) rectangle (-1,1) (-1.5,0) node[below]
        {\tiny\rotatebox{-90}{\texttt{\textbf{Noircir la case}}}};''']

    # Generate the corresponding names table in LaTeX.
    for i, name in enumerate(reversed(names)):
        # Troncate long names.
        if len(name) >= 15:
            _name = name[:13].strip()
            if " " not in name[12:13]:
                _name += "."
            name = _name
        a = 2*i
        b = a + 1
        c = a + 0.5
        color = ('black' if _n_student == len(names) - i else 'white')
        content.append(fr'''\draw[fill={color}] ({a},0) rectangle ({b},1) ({c},0)
            node[below] {{\tiny \rotatebox{{-90}}{{\texttt{{{name}}}}}}};''')
    b += 1
    content.append(fr'''\draw[rounded corners] (-3,2) rectangle ({b}, -6.5);
        \draw[] (-0.5,2) -- (-0.5,-6.5);
        \end{{tikzpicture}}
        \end{{center}}
        \vspace{{-1em}}
        ''')
    return '\n'.join(content)




def student_ID_table(ID_length, max_ndigits, digits):
    """"Generate a table where the student will write its identification number.

    The table have a row for each digit, where the student check corresponding
    digit to indicate its number.

    Parameters:
    - the length of an ID,
    - the maximal number of different digits in an ID caracter,
    - a list of sets corresponding to the different digits used for each ID caracter.

    Return: LaTeX code.
    """
    content = []
    write = content.append
    write('\n\n')
    write(r'\begin{tikzpicture}[baseline=-10pt,scale=.5]')
    write(r'\node[anchor=south west] at (-1, 0) {Numéro étudiant (INE)~:};')
    write(r'\draw[] (-1, 0) node {\zsavepos{ID-table}} rectangle (0,%s);' % (-ID_length))
    for j in range(ID_length):
        # One row for each digit of the student id number.
        for i, d in enumerate(sorted(digits[j])):
            write(fr'''\draw ({i},{-j}) rectangle ({i+1},{-j-1})
                    ({i+0.25},{-j-0.25}) node  {{\footnotesize\color{{black}}\textsf{{{d}}}}};''')
        for i in range(i, max_ndigits):
            write(fr'''\draw ({i},{-j}) rectangle ({i+1},{-j-1});''')
    write(r'\draw[black,->,thick] (-0.5, -0.5) -- (-0.5,%s);' % (0.5 - ID_length))
    write(r'\end{tikzpicture}')
    write(r'\hfill\begin{tikzpicture}[baseline=10pt]'
          r'\node[draw,rounded corners] {\begin{tabular}{p{8cm}}'
          r'\textsc{Nom~:}~\dotfill\\'
          r'Prénom~:~\dotfill\\'
          r'Groupe~:~\dotfill\\'
          r"Numéro d'étudiant:~\dotfill\\"
          r'\end{tabular}};\end{tikzpicture}'
          r'\write\mywrite{ID-table: '
          r'(\dimtomm{\zposx{ID-table}sp}, '
          r'\dimtomm{\zposy{ID-table}sp})}')
    write('\n\n')
    return '\n'.join(content)



def table_for_answers(config, ID=None):
    """Generate the table where students select correct answers.

    - `config` is a dict generated when compiling test.
    - `ID` is the student ID if correct answers should be shown.
      If `ID` is `None` (default), the table will be blank.
    """
    content = []
    write = content.append

    # Generate the table where students will answer.
    tkzoptions = ['scale=%s' % CELL_SIZE_IN_CM]

    d = config['ordering'][1 if ID is None else ID]
    questions = d['questions']
    answers = d['answers']
    n_questions = len(questions)
    n_max_answers = max(len(l) for l in answers.values())
    flip = (n_max_answers > n_questions)
    if flip:
        tkzoptions.extend(['x={(0cm,-1cm)}', 'y={(-1cm,0cm)}'])

    write(r"""
        \begin{tikzpicture}[%s]
        \draw[thin,fill=black] (-1,0) rectangle (0,1);""" % (','.join(tkzoptions)))

    for x1 in range(n_questions):
        x2=x1 + 1
        x3=.5*(x1 + x2)
        write(fr"\draw[ultra thin] ({x1},0) rectangle ({x2},1) ({x3},0.5) "
              fr"node {{{x1 + 1}}};")

    # Find correct answers numbers for each question.
    if ID is not None:
        correct_ans = correct_answers(config, ID)

    i = -1
    for i in range(n_max_answers):
        name = ascii_letters[i]
        y1 = -i
        y2 = y1 - 1
        y3 = .5*(y1 + y2)
        write("\n"
              fr"\draw[ultra thin] (-1,{y1}) rectangle (0,{y2}) (-0.5,{y3}) "
              fr"node {{{name}}};")
        for j in range(n_questions):
            x1 = j
            x2 = x1 + 1
            opt = ''
            if ID is not None and i + 1 in correct_ans[j + 1]:
                opt = 'fill=gray'
            write(fr"\draw [ultra thin,{opt}] ({x1},{y1}) rectangle ({x2},{y2});")

    write(fr"\draw [thick] (-1,1) rectangle ({x2},{y2});" "\n")
#              %\draw [thick] (-1,0) -- ({x2},0);

    for i in range(0, x2):
        write(fr"\draw [thick] ({i},1) -- ({i},{y2});" "\n")

    write(r"\end{tikzpicture}\hfill\hfill\hfil" "\n")

    return '\n'.join(content)



def packages_and_macros():
    "Generate LaTeX default header (loading LaTeX packages and defining some custom macros)."
    # https://tex.stackexchange.com/questions/37297/how-to-get-element-position-in-latex
    paper_format = f'{PAPER_FORMAT.lower()}paper'
    # LaTeX header is in two part, so as user may insert some customization here.
    return [fr"""\documentclass[{paper_format},twoside,10pt]{{article}}
    \PassOptionsToPackage{{utf8}}{{inputenc}}
    \PassOptionsToPackage{{document}}{{ragged2e}}
    \PassOptionsToPackage{{left={MARGIN_LEFT_IN_CM}cm,
        right={MARGIN_RIGHT_IN_CM}cm,
        top={MARGIN_TOP_IN_CM}cm,bottom={MARGIN_BOTTOM_IN_CM}cm}}{{geometry}}
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
    """,
    # <Custom packages will be loaded just here.>
    r"""\usepackage{inputenc}
    \usepackage{ragged2e}
    \usepackage{geometry}
    \usepackage{pifont}
    \usepackage{textcomp}
    \usepackage{nopageno}
    \usepackage{tikz}
    \usepackage{zref-user}
    \usepackage{zref-abspos}
    \usepackage{zref-abspage}
    \usepackage{zref-lastpage}
    \usepackage{everypage}
    \usepackage{tabularx}
    \usetikzlibrary{calc}
    \usetikzlibrary{math}
    \makeatletter
    \newcommand\dimtomm[1]{%
        \strip@pt\dimexpr 0.351459804\dimexpr#1\relax\relax%
    }
    \makeatother
    \newcommand{\checkBox}[2]{%
        \begin{tikzpicture}[baseline=-12pt,color=black, thick]
            \draw[fill=#1] (0,0)
                node {\zsavepos{#2-ll}}
                rectangle (.5,-.5);
        \end{tikzpicture}%
        \write\mywrite{#2: p\thepage, (%
            \dimtomm{\zposx{#2-ll}sp},
            \dimtomm{\zposy{#2-ll}sp})%
        }%
    }
    \newwrite\mywrite
    \openout\mywrite=\jobname.pos\relax
    \usepackage{enumitem} % To resume an enumeration.
    \setenumerate[0]{label=\protect\AutoQCMcircled{\arabic*}}
    \AddEverypageHook{\CustomHeader}

    \newlength{\AutoQCMTabLength}
    \newcommand{\AutoQCMTab}[2]{%
      \settowidth{\AutoQCMTabLength}{#1{}#2}
      \ifdim \AutoQCMTabLength<\textwidth%
      \begin{tabular}{l@{\,\,}l}#1&#2\end{tabular}%
      \else%
      \begin{tabularx}{\linewidth}{l@{\,\,}X}#1&#2\end{tabularx}%
      \fi%
    }
    """]



def answers_and_score(config, name, identifier, score, max_score):
    "Generate plain LaTeX code corresponding to score and correct answers."
    table = table_for_answers(config, identifier)
    if score is not None:
        score = \
            r'''\begin{tikzpicture}
            \node[draw,very thick,rectangle, rounded corners,red!70!black] (0,0) {
            \begin{Large}
            Score~: %(score)s/%(max_score)s
            \end{Large}};
            \end{tikzpicture}''' % locals()
    else:
        score = ''
    left = MARGIN_LEFT_IN_CM
    right = MARGIN_RIGHT_IN_CM
    top = MARGIN_TOP_IN_CM
    bottom = MARGIN_BOTTOM_IN_CM
    paper = PAPER_FORMAT
    return (r"""
    \documentclass[%(paper)s,10pt]{article}
    \usepackage[utf8]{inputenc}
    \usepackage[document]{ragged2e}
    \usepackage{nopageno}
    \usepackage{tikz}
    \usepackage[left=%(left)scm,right=%(right)scm,top=%(top)scm,bottom=%(bottom)scm]{geometry}
    \parindent=0cm
    \usepackage{textcomp}

    \begin{document}
    \begin{Large}\textsc{%(name)s}\end{Large}
    \hfill%(score)s

    \bigskip

    Solution~:
    \medskip

    %(table)s

    \end{document}
    """ % locals())



