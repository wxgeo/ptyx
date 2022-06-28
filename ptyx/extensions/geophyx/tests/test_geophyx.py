"""
QUESTIONS

This extension offers a new syntaw to write tests and answers.
"""


from ptyx.latex_generator import Compiler


def test_CALC():
    test = r"$#CALC{\dfrac{2}{3}+1}=#RESULT$ et $#CALC[a]{\dfrac{2}{3}-1}=#a$"
    c = Compiler()
    latex = c.parse("#LOAD{geophyx}" + test)
    print(latex)
    assert latex == r"$\dfrac{2}{3}+1=\frac{5}{3}$ et $\dfrac{2}{3}-1=- \frac{1}{3}$"


def test_TABVAR():
    test = (
        "$#{a=2;}\\alpha=#{alpha=3},\\beta=#{beta=5}\n\n"
        "#TABVAR[limites=False,derivee=False]f(x)=#a*(x-#alpha)^2+#beta#END_TABVAR$"
    )
    result = """$\\alpha=3,\\beta=5
\\setlength{\\TVextraheight}{\\baselineskip}
\\[\\begin{tabvar}{|C|CCCCC|}
\\hline
\\,\\,x\\,\\,                            &-\\infty      &        &3&      &+\\infty\\\\
\\hline
\\niveau{1}{2}\\raisebox{0.5em}{$f(x)$}&\\niveau{2}{2}&\\decroit&5&\\croit&\\\\
\\hline
\\end{tabvar}\\]
% x;f(x):(-oo;) >> (3;5) << (+oo;)
% f(x)=2*(x-3)^2+5\n$"""
    c = Compiler()
    latex = c.parse("#LOAD{geophyx}" + test)
    assert latex == result
