from importlib import reload
from os.path import dirname
from numpy import array

from scriptlib import command, cd
import generate
import scan


def compile_and_scan(name):
    command("pdflatex -interaction=nonstopmode %s.tex" % name)
    command("inkscape -f %s.pdf -b white -d 150 -e %s.png" % (name, name))
    return scan.scan_picture("%s.png" % name, "%s.config" % name)


def test1():
    cd(dirname(__file__))
    #~ reload(generate)
    #~ reload(scan)
    id0 = 1173
    # 1173 = 1 + 4 + 16 + 128 + 1024 → ■■□■□■□□■□□■□□□□
    #
    #     ■   ■ □ ■ □ ■  □  □   ■   □   □   ■    □    □    □     □
    #   start 1 2 4 8 16 32 64 128 256 512 1024 2048 4096 8192 16384
    questions0 = ["A1","A2","B1","B2","C", "D", "E1", "E2", "E3",
                    10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
    n_answers0 = 5
    n_student0 = 27
    name = "test1"
    intro = r"""\begin{tikzpicture}[scale=0.5]
        \draw[rounded corners] (0,1) rectangle (14,-5);
        \draw[rounded corners,fill=gray!20!white] (0,-3) rectangle (14,-5);
        \draw[fill=white]  (0,0) rectangle (14,-4);
        \draw (0,0) -- (14,0) (7,0.5) node {\small\decofourleft\quad\textbf{\textsc{Interrogation Écrite n\textdegree{}3}}\quad\decofourright};
        \draw (0,0) node [below right] {\small\begin{minipage}{6cm}
                                        \begin{itemize}
                                         \item 1 bonne réponse rapporte 1 point
                                         \item 1 mauvaise réponse enlève 0,25 point
                                         \item l'absence de réponse n'enlève ni ne rajoute aucun point
                                        \end{itemize}
                                       \end{minipage}};

        \draw (0,-4) -- (14,-4) (7,-4.5) node {\small\textbf{Répondez dans le tableau ci-contre \ding{43}}};
        \end{tikzpicture}
        \hfill"""

    generate.generate_ptyx_code(filename=name, identifier=id0,
                 questions=questions0,
                 answers=n_answers0,
                 introduction=intro,
                 options={
                 (2, 3):"fill=blue!50!gray!50!white",
                 (4, 1): "fill=black",
                 (7, 2): "fill=red",
                 (19, 4):"fill=green!50!gray!50!white",
                 (19, 3):"fill=black!20!white",
                 },
                 #_n_student=n_student0,
                           )
    id1, answers, n_student1 = compile_and_scan(name)

    assert id1 == id0
    #assert n_student1 == n_student0
    assert len(questions0) == len(answers)
    assert all(n_answers0 == len(answer) for answer in answers)
    assert (array(answers).nonzero() == array(([2, 4, 7, 19, 19], [3, 1, 2, 3, 4]))).all()

    return ((id1, answers, n_student1))

def test2():
    reload(generate)
    reload(scan)
    id0 = 27
    questions0 = 20
    n_answers0 = 8
    name = "test2"

    generate.generate_ptyx_code(filename=name, identifier=id0,
                 questions=questions0,
                 answers=n_answers0,
                 options={
                 (2, 3):"fill=blue!50!gray!50!white",
                 (4, 1): "fill=black",
                 (7, 2): "fill=red",
                 (19, 4):"fill=green!50!gray!50!white",
                 (19, 3):"fill=black!20!white",
                 },
                           )
    id1, answers, n_student1 = compile_and_scan(name)

    assert id1 == id0
    assert n_student1 is None
    assert questions0 == len(answers)
    assert all(n_answers0 == len(answer) for answer in answers)
    assert (array(answers).nonzero() == array(([2, 4, 7, 19, 19], [3, 1, 2, 3, 4]))).all()

    return ((id1, answers, n_student1))



