import pytest

from ptyx.errors import PythonBlockError, PythonExpressionError, PtyxSyntaxError
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
