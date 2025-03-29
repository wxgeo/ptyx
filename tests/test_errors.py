import pickle

import pytest
from ptyx.latex_generator import Compiler

from ptyx.errors import PythonBlockError, PythonExpressionError, PtyxSyntaxError, ErrorInformation
from tests import parse


def test_error_in_python_code():
    code = """
#PYTHON
a = 0
b = 1 / a
#END_PYTHON"""
    with pytest.raises(PythonBlockError) as exc_info:
        parse(code)
    error = exc_info.value
    assert isinstance(error.__cause__, ZeroDivisionError)
    assert error.python_code.strip() == "a = 0\nb = 1 / a"
    code = """
#PYTHON
a = [1 2]
#END_PYTHON"""
    with pytest.raises(PythonBlockError) as exc_info:
        parse(code)
    error = exc_info.value
    assert isinstance(error.__cause__, SyntaxError)
    assert error.python_code.strip() == "a = [1 2]"


def test_error_in_expression_evaluation():
    with pytest.raises(PythonExpressionError) as exc_info:
        parse("#{1+None}")
    error = exc_info.value
    assert isinstance(error.__cause__, TypeError)
    assert error.python_code == "1+None"


def test_invalid_IF_arg():
    with pytest.raises(PythonExpressionError) as exc_info:
        parse("#IF{()[0]} #END")
    error = exc_info.value
    assert isinstance(error.__cause__, IndexError)
    assert error.python_code == "()[0]"


def test_unclosed_python_block():
    with pytest.raises(PtyxSyntaxError) as exc_info:
        parse("#PYTHON")
    assert exc_info.value.args[0] == "#PYTHON tag must be close with a #END_PYTHON tag."


@pytest.mark.xfail
def test_invalid_syntax():
    with pytest.raises(PtyxSyntaxError) as exc_info:
        parse("#IF{4==4} #END_CASE")
    error = exc_info.value
    assert isinstance(error.__cause__, TypeError)
    assert error.python_code == ""


def test_PythonBlockError():
    # Test that accurate error information is gathered.
    # 1. Test a syntax error.
    with pytest.raises(PythonBlockError) as exc_info:
        code = "\na = 5\nb = ?\nc = 3\n"
        try:
            exec(code)
        except Exception as e:
            raise PythonBlockError(python_code=code) from e
    assert exc_info.value.info == ErrorInformation("SyntaxError", "invalid syntax", 3, 3, 5, 6)

    # 2. Test a runtime error.
    with pytest.raises(PythonBlockError) as exc_info:
        code = "\na = 5\nb = 1/0\nc = 3\n"
        try:
            exec(code)
        except Exception as e:
            raise PythonBlockError(python_code=code) from e
    assert exc_info.value.info == ErrorInformation("ZeroDivisionError", "division by zero", 3, 3, 4, 7)

    # The faulty line must be colored in yellow in the report:
    assert (
        exc_info.value.pretty_report.split("\n")[6] == "\x1b[33m│ 3 │ b = 1/0                        │\x1b[0m"
    )

    # 3. Test when python code contain comments.
    with pytest.raises(PythonBlockError) as exc_info:
        code = "\na = 5\n# Some comment\nb = 1/0\nc = 3\n"
        try:
            exec(code)
        except Exception as e:
            raise PythonBlockError(python_code=code) from e

    # The faulty line must be colored in yellow in the report:
    assert (
        exc_info.value.pretty_report.split("\n")[7] == "\x1b[33m│ 4 │ b = 1/0                        │\x1b[0m"
    )


def test_PythonBlockError_full_pretty_report():
    with pytest.raises(PythonBlockError) as exc_info:
        # (Use case-sensitive code, to prevent notably regressions
        # for a previous bug concerning upper/lower case).
        code = "\nl = []\nif len(L) > 1:\n    print(l[1])"
        try:
            exec(code)
        except Exception as e:
            raise PythonBlockError(python_code=code) from e
    assert exc_info.value.info == ErrorInformation(
        type="NameError", message="name 'L' is not defined", row=3, end_row=3, col=7, end_col=8
    )

    # The faulty line must be colored in yellow in the report:
    assert exc_info.value.pretty_report == "\n".join(
        [
            "",
            "╭────────────────────────────────────╮",
            "│ ✎ Executing following python code: │",
            "├────────────────────────────────────┤",
            "│ 1 │                                │",
            "│ 2 │ l = []                         │",
            "\x1b[33m│ 3 │ if len(L) > 1:                 │\x1b[0m",
            "│ 4 │     print(l[1])                │",
            "╰────────────────────────────────────╯",
            "",
            "\x1b[31m[ERROR] \x1b[0m\x1b[33mNameError: Name 'L' is not defined.\x1b[0m",
        ]
    )


def test_PythonBlockError_pickling():
    code = "#PYTHON\nt = (4\n#END_PYTHON"
    try:
        compiler = Compiler()
        compiler.parse(code=code)
        assert False  # A PythonBlockError should have been raised!
    except BaseException as e:
        # Pickle error before accessing its information (because PythonBlockError has a cache,
        # so we have to test that the cache is automatically updated before pickling. If we access
        # information first, it would update the cache and the test would be less exhaustive).
        pickled_err = pickle.loads(pickle.dumps(e))
        assert isinstance(e, PythonBlockError)
        assert isinstance(pickled_err, PythonBlockError)
        assert e.info.message == "'(' was never closed"
        assert pickled_err.info.message == "'(' was never closed"
