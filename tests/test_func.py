import pytest

from ptyx.printers import sympy2latex
from ptyx.utilities import (
    find_closing_bracket,
    round_away_from_zero,
    extract_verbatim_tag_content,
    restore_verbatim_tag_content,
)


def test_find_closing_bracket():
    assert find_closing_bracket("{hello{world} !} etc.", 1) == 15
    assert find_closing_bracket("{'}'}", 1) == 4
    assert find_closing_bracket("{'}'}", 1, detect_strings=False) == 2
    # Unbalanced
    with pytest.raises(ValueError, match="ERROR: unbalanced brackets"):
        find_closing_bracket("{'}' '}")
    assert find_closing_bracket("[o[k]]", 1, brackets="[]") == 5


def test_find_closing_bracket_escape_char():
    # Support \\ to escape ' or " character
    assert find_closing_bracket("{'}\\''}", 1) == 6
    assert find_closing_bracket('{"\'}\\""}', 1) == 7
    # Unbalanced
    with pytest.raises(ValueError, match="ERROR: unbalanced brackets"):
        assert find_closing_bracket("{'}\\\\''}", 1) == 6
    assert find_closing_bracket("{'}\\\\\\''}", 1) == 8


def test_round():
    assert round_away_from_zero(1.775, 2) == 1.78

    assert round_away_from_zero(1.454, -2) == 0
    assert round_away_from_zero(1.454, -1) == 0
    assert round_away_from_zero(1.454) == 1
    assert round_away_from_zero(1.454, 1) == 1.5
    assert round_away_from_zero(1.454, 2) == 1.45
    assert round_away_from_zero(1.454, 3) == 1.454
    assert round_away_from_zero(1.454, 4) == 1.454

    assert round_away_from_zero(-9.545, -2) == 0
    assert round_away_from_zero(-9.545, -1) == -10
    assert round_away_from_zero(-9.545) == -10
    assert round_away_from_zero(-9.545, 1) == -9.5
    assert round_away_from_zero(-9.545, 2) == -9.55
    assert round_away_from_zero(-9.545, 3) == -9.545
    assert round_away_from_zero(-9.545, 4) == -9.545

    assert round_away_from_zero(float("inf"), 4) == float("inf")
    assert round_away_from_zero(float("-inf"), 4) == float("-inf")
    assert str(round_away_from_zero(float("nan"), 4)) == "nan"


def test_sympy2latex():
    assert sympy2latex(0.0) == "0"
    assert sympy2latex(-2.0) == "-2"
    assert sympy2latex(-0.0) == "0"
    # Issue with sympy 1.7+
    assert sympy2latex("hello") == "hello"


def test_extract_verbatim_tag_content():
    code = (
        "hello\n#VERBATIM\ndef f(x):\n  return x+1\n#END\nguten Tag\n#VERBATIM\na = 5\n#END_VERBATIM\nbonjour"
    )
    new_code, substitutions = extract_verbatim_tag_content(code)
    assert substitutions == ["#VERBATIM\ndef f(x):\n  return x+1\n#END", "#VERBATIM\na = 5\n#END_VERBATIM"]
    assert new_code == "hello\n#VERBATIM\n#END\nguten Tag\n#VERBATIM\n#END\nbonjour"
    assert restore_verbatim_tag_content(new_code, substitutions) == code
