import traceback

from ptyx.shell import yellow


class PtyxDocumentCompilationError(RuntimeError):
    """Error raised when a pTyX document can't be compiled.

    This is a generic error, and should not be raised directly (use one of its subclasses instead).

    All errors originating from a faulty pTyX usage should raise an exception inheriting from this class.
    However, errors likely to indicate a bug in pTyX itself should never use them, to avoid confusion.
    """

    def __init__(self, *args):
        super().__init__(*args)


class PtyxExtensionNotFound(PtyxDocumentCompilationError):
    """Error raised when a document contains #LOAD{extension} and extension is not found."""


class PtyxSyntaxError(PtyxDocumentCompilationError):
    """Error raised when the syntax tree can't be generated when parsing pTyX code."""


class PtyxRuntimeError(PtyxDocumentCompilationError):
    """Error raised if something went wrong when generating LaTeX from a pTyX tag."""


class PythonCodeError(PtyxDocumentCompilationError):
    """Error raised when something wrong occurred during the execution of embedded python code.

    Specific arguments:
        - python_code: the code whose execution failed.
        - label: a label referencing the code snippet, to retrieve
    """

    def __init__(self, *args, python_code: str = None, label=None):
        super().__init__(*args)
        self.python_code = python_code
        self.label = label


class PythonExpressionError(PythonCodeError):
    """Error raised when something wrong occurred during the execution of an embedded block of python code.

    Example of faulty python expression:

        #{a=0;b=1/a}
    """

    def __init__(self, *args, python_code: str = None, flags: str = None, label=None, ptyx_tag: str = ""):
        super().__init__(*args, python_code=python_code, label=label)
        self.flags = flags
        self.ptyx_tag = ptyx_tag

    @property
    def pretty_report(self) -> str:
        if self.python_code is None:
            return "<No python code found>"
        flags = "" if self.flags is None else f"[{yellow(self.flags)}]"
        if self.python_code is None:
            return "<No python code found>"
        msg = f"#{self.ptyx_tag}{flags}{{{yellow(self.python_code)}}}"
        if self.__cause__ is not None:
            msg += "\n" + yellow(self.__cause__)
        return msg


class PythonBlockError(PythonCodeError):
    """Error raised when something wrong occurred during the execution of an embedded block of python code.

    Example of faulty python block:

        #PYTHON
        a = 0
        b = 1 / a
        #END_BLOCK
    """

    @property
    def pretty_report(self) -> str:
        if self.python_code is None:
            return "<No python code found>"
        msg = format_python_code_snippet(self.python_code)
        e = self.__cause__
        if isinstance(e, SyntaxError) and e.filename == "<string>":
            assert e.lineno is not None
            i = e.lineno + 4
            msg[i] = yellow(msg[i])
            msg.append(f"\n{yellow(e.msg)}")
        else:
            assert e is not None
            for tb in traceback.extract_tb(e.__traceback__):
                if tb.name in ("<module>", "<string>") and isinstance(tb.lineno, int):
                    i = tb.lineno + 4
                    msg[i] = yellow(msg[i])
                    break
        return "\n".join(msg)


def format_python_code_snippet(python_code: str) -> list[str]:
    """Return a list of prettified lines of python code, ready to be printed."""
    msg = ["", "%s %s Executing following python code:" % (chr(9474), chr(9998))]
    lines = [""] + python_code.split("\n") + [""]
    zfill = len(str(len(lines)))
    msg.extend(
        "%s %s %s %s" % (chr(9474), str(i).zfill(zfill), chr(9474), line) for i, line in enumerate(lines)
    )
    n = max(len(s) for s in msg)
    msg.insert(1, chr(9581) + n * chr(9472))
    msg.insert(3, chr(9500) + n * chr(9472))
    msg.append(chr(9584) + n * chr(9472))
    assert isinstance(python_code, str)
    return msg
