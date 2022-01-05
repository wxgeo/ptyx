from json import loads, dumps as _dumps, JSONEncoder
from typing import Dict, Set, Any, Tuple, Optional


class CustomJSONEncoder(JSONEncoder):
    def default(self, obj):
        # Save sets as tuples.
        if isinstance(obj, set):
            return tuple(obj)
        # Let the base class default method raise the TypeError
        return JSONEncoder.default(self, obj)


def dumps(o):
    return _dumps(o, ensure_ascii=False, cls=CustomJSONEncoder)


def fmt(s: str) -> str:
    return s.upper().center(40, "-")


def encode2js(o, formatter=(lambda s: s), _level=0):
    """Encode dict `o` to JSON.

    If `formatter` is set, it must be a function used to format first-level
    keys of `o`."""
    if _level == 0 and not isinstance(o, dict):
        raise NotImplementedError
    if isinstance(o, dict):
        if _level == 0:
            blocks = []
            for k, v in o.items():
                blocks.append(f'"{formatter(k)}":\n' + encode2js(v, _level=_level + 1))
            return "{\n\n%s\n\n}" % ",\n\n".join(blocks)
        else:
            blocks = []
            indent = (_level - 1) * "\t"
            for k, v in o.items():
                blocks.append(f'{indent}"{k}": ' + encode2js(v, _level=_level + 1))
            return "{\n%s\n%s}" % (",\n".join(blocks), indent)
    elif isinstance(o, (tuple, set, list)):
        assert _level != 0
        if _level == 1:
            return "[\n%s\n]" % ",\n".join(dumps(v) for v in o)
        else:
            return dumps(o)
    else:
        return dumps(o)


def keys2int(d: Dict[str, Any]) -> Dict[int, Any]:
    return {(int(k) if k.isdecimal() else k): v for k, v in d.items()}


def decodejs(js):
    d = loads(js, object_hook=keys2int)
    new_d = {}
    # Strip '-' from keys and convert them to lower case.
    for key in d:
        new_d[key.strip("-").lower()] = d[key]
    d = {}
    # Students ID must be strings.
    for key in new_d["ids"]:
        d[str(key)] = new_d["ids"][key]
    new_d["ids"] = d
    return new_d


def dump(path, cfg):
    """Dump `cfg` dict to `path` as json."""
    with open(path, "w") as f:
        f.write(encode2js(cfg, formatter=fmt))


def load(path):
    """Load `path` configuration file (json) and return a dict."""
    with open(path) as f:
        js = f.read()
    return decodejs(js)


def real2apparent(
    original_q_num: int, original_a_num: Optional[int], config: dict, doc_id: int
) -> Tuple[int, int]:
    """Return apparent question number and answer number.

    If `a` is None, return only question number.

    By "apparent", it means question and answer numbers as they
    will appear in the PDF file, after shuffling questions and answers.

    Arguments `q` and `a` are real question and answer numbers, that is
    the ones before questions and answers were shuffled."""
    questions = config["ordering"][doc_id]["questions"]
    answers = config["ordering"][doc_id]["answers"]
    # Apparent question number (ie. after shuffling).
    # Attention, list index 0 corresponds to question number 1.
    pdf_q_num = questions.index(original_q_num) + 1
    if original_a_num is None:
        return pdf_q_num
    for pdf_a_num, (ans_num, is_correct) in enumerate(answers[original_q_num], start=1):
        if ans_num == original_a_num:
            return (pdf_q_num, pdf_a_num)
    raise IndexError(f"Answer {original_a_num} not found for question {original_q_num}.")


def apparent2real(
    pdf_q_num: int, pdf_a_num: Optional[int], config: dict, doc_id: int
) -> Tuple[int, int]:
    """Return real question number and answer number.

    If `a` is None, return only question number.
    """
    questions = config["ordering"][doc_id]["questions"]
    answers = config["ordering"][doc_id]["answers"]
    # Real question number (ie. before shuffling).
    # Attention, first question is numbered 1, corresponding to list index 0.
    original_q_num = questions[pdf_q_num - 1]
    if pdf_a_num is None:
        return original_q_num
    # Real answer number (ie. before shuffling).
    original_a_num = answers[original_q_num][pdf_a_num - 1][0]
    return (original_q_num, original_a_num)


def is_answer_correct(
    q_num: int, a_num: int, config: dict, doc_id: int, use_original_num: bool = True
) -> bool:
    if use_original_num:
        # q_num and a_num are question and answer number *before* shuffling questions.
        for original_a_num, is_correct in config["ordering"][doc_id]["answers"][q_num]:
            if original_a_num == a_num:
                return is_correct
        raise IndexError(f"Answer {a_num} not found.")
    else:
        # q_num and a_num are question and answer number *after* shuffling questions.
        original_q_num = config["ordering"][doc_id]["questions"][q_num - 1]
        return config["ordering"][doc_id]["answers"][original_q_num][a_num - 1][1]


def get_correct_answers(
    config: dict, use_original_num: bool = True
) -> Dict[int, Dict[int, Set[int]]]:
    """Return a dict containing the set of the correct answers for each question for each document ID.

    Correct answers numbers returned are apparent one (i.e. after shuffling).
    """
    correct_answers_by_id = {}
    for doc_id in config["ordering"]:
        correct_answers = {}
        questions = config["ordering"][doc_id]["questions"]
        answers = config["ordering"][doc_id]["answers"]
        for i, q in enumerate(questions, start=1):
            # `i` is the 'apparent' question number.
            # `q` is the 'real' question number, i.e. the question number before shuffling.
            # `j` is the 'apparent' answer number.
            # `a` is the 'real' answer number, i.e. the answer number before shuffling.
            if use_original_num:
                correct_answers[q] = {a for (a, _is_correct) in answers[q] if _is_correct}
            else:
                correct_answers[i] = {
                    j for (j, (a, _is_correct)) in enumerate(answers[q], start=1) if _is_correct
                }
        correct_answers_by_id[doc_id] = correct_answers
    return correct_answers_by_id
