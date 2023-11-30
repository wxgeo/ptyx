from dataclasses import dataclass
from enum import Enum, auto
from typing import TypedDict


class ParamDict(TypedDict):
    tex_command: str
    quiet_tex_command: str
    sympy_is_default: bool
    import_paths: list[str]
    debug: bool
    floating_point: str
    win_print_command: str


class CustomParamDict(TypedDict, total=False):
    tex_command: str
    quiet_tex_command: str
    sympy_is_default: bool
    import_paths: list[str]
    debug: bool
    floating_point: str
    win_print_command: str


class NiceOp(Enum):
    NONE = auto()
    ADD = auto()
    SUB = auto()
    MUL = auto()
    EQ = auto()


class PickItemAction(Enum):
    NONE = auto()
    SELECT_FROM_NUM = auto()
    RAND_CHOICE = auto()


@dataclass(kw_only=True)
class EvalFlags:
    is_mul_coeff: bool = False
    eval_as_float: bool = False
    keep_dot_as_decimal_mark: bool = False
    format_as_str: bool = False
    round: int | None = None
    previous_nice_op: NiceOp = NiceOp.NONE
    round_result: bool = False
    result_is_exact: bool | None = None
    pick_action: PickItemAction = PickItemAction.NONE
    suppress_next_eval: bool = False
