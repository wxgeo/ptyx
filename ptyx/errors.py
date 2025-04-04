from dataclasses import dataclass, field
import traceback
from typing import Any

from ptyx.internal_types import PtyxTraceback

from ptyx.pretty_print import yellow, red, pretty_box


def _cap(s: str) -> str:
    """Capitalize the first letter of string `s`."""
    return s[:1].upper() + s[1:]


@dataclass
class ErrorInformation:
    """Standardized information about errors.

    This is motivated by the lack of a common interface between syntax errors
    and runtime errors in python.
    """

    type: str = ""
    message: str = ""
    row: int | None = None
    end_row: int | None = None
    col: int | None = None
    end_col: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)


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

    Specific (optional) arguments:
        - python_code: the code whose execution failed.
        - label: a label referencing the code snippet, to retrieve it.
    """

    def __init__(
        self,
        *args,
        python_code: str = None,
        label=None,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(*args)
        self.python_code = python_code
        self.label = label
        # When transferring an error from one process to another (using multiprocessing.Queue for example),
        # the error must be pickled. By default,
        self._info: ErrorInformation | None = None
        self.ptyx_traceback: PtyxTraceback | None = context.get("PTYX_TRACEBACK") if context else None

    def __getstate__(self):
        # Update self._info cache before getting state for pickling.
        _ = self.info
        return super().__getstate__()

    @property
    def info(self) -> ErrorInformation:
        if self._info is None:
            self._info = self._collect_info()
        return self._info

    def _collect_info(self) -> ErrorInformation:
        error = self.__cause__
        if isinstance(error, SyntaxError) and error.filename == "<string>":
            return ErrorInformation(
                type(error).__name__,
                error.msg,
                error.lineno,
                error.end_lineno,
                error.offset,
                error.end_offset,
            )
        elif error is not None:
            for tb in traceback.extract_tb(error.__traceback__):
                if tb.name in ("<module>", "<string>") and isinstance(tb.lineno, int):
                    return ErrorInformation(
                        type(error).__name__,
                        str(error),
                        tb.lineno,
                        tb.end_lineno,
                        tb.colno,
                        tb.end_colno,
                    )
        return ErrorInformation()


class PythonExpressionError(PythonCodeError):
    """Error raised when something wrong occurred during the execution of an embedded block of python code.

    Example of faulty python expression:

        #{a=0;b=1/a}
    """

    def __init__(
        self,
        *args,
        python_code: str = None,
        flags: str = None,
        label=None,
        context: dict[str, Any] | None = None,
        ptyx_tag: str = "",
    ):
        super().__init__(*args, python_code=python_code, label=label, context=context)
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

    def __init__(
        self,
        *args,
        python_code: str = None,
        label: str = None,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(*args, python_code=python_code, label=label, context=context)

    @property
    def pretty_report(self) -> str:
        if self.python_code is None:
            return "<No python code found>"
        msg = [f"File {self.ptyx_traceback[-1][0]}"] if self.ptyx_traceback else []
        msg.extend(format_python_code_snippet(self.python_code))
        error_info = self.info
        i = error_info.row
        if i is not None:
            i += 3  # 3 lines for the header of the box.
            # Color in yellow the faulty line.
            msg[i] = yellow(msg[i])
        # Append the error message after the information box.
        content = f"{error_info.type}: {_cap(error_info.message)}."
        msg.append(f"\n{red('[ERROR] ')}{yellow(content)}")
        return "\n".join(msg)


def format_python_code_snippet(python_code: str) -> list[str]:
    """Return a list of prettified lines of python code, ready to be printed."""
    return pretty_box(python_code, title="Executing following python code:")
