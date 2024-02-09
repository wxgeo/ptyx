from tests import parse


def test_PYTHON_tag():
    code = r"""
#PYTHON
a = 2 # test for comment support
#END_PYTHON
#a
"""
    assert parse(code) == "\n2\n"


def test_PYTHON_tag_bug():
    code = r"""
#PYTHON
print("#END")
a = 2 # test for comment support
#END_PYTHON
#a
"""
    assert parse(code) == "\n2\n"


def test_hashtag_inside_python_block():
    code = """
    #PYTHON
    s = "#" # This should not be a problem.
    t = "#test" # Neither this.
    #END_PYTHON
    #s #t
    """
    assert parse(code) == "\n    # #test\n    "


def test_tagged_python():
    code = """
#PYTHON:125:
a = 7
#END_PYTHON
#a"""
    assert parse(code).strip() == "7"


def test_tagged_eval():
    code = """#{:17:a=3}"""
    assert parse(code) == "3"
