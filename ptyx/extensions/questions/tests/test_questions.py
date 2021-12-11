from os.path import join, dirname

from ptyx.extensions.questions import main


def test_question():
    with open(join(dirname(__file__), "in.txt")) as f:
        questions_text = f.read()

    with open(join(dirname(__file__), "out.ptyx")) as f:
        expected_ptyx_code = f.read()

    assert main(questions_text, None) == expected_ptyx_code
