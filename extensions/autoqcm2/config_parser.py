from json import loads, dumps as _dumps, JSONEncoder


class CustomJSONEncoder(JSONEncoder):
    def default(self, obj):
        # Save sets as tuples.
        if isinstance(obj, set):
            return tuple(obj)
        # Let the base class default method raise the TypeError
        return JSONEncoder.default(self, obj)

def dumps(o):
    return _dumps(o, ensure_ascii=False, cls=CustomJSONEncoder)

def fmt(s):
    return s.upper().center(40,"-")

def encode2js(o, fmt=(lambda s:s), _level=0):
    """Encode dict `o` to JSON.

    If `fmt` is set, it must be a function used to format first-level
    keys of `o`."""
    if _level == 0 and not isinstance(o, dict):
        raise NotImplementedError
    if isinstance(o, dict):
        if _level == 0:
            l = []
            for k, v in o.items():
                l.append(f'"{fmt(k)}":\n' +
                         encode2js(v, _level=_level+1))
            return "{\n\n%s\n\n}" % ',\n\n'.join(l)
        else:
            l = []
            indent = (_level - 1)*'\t'
            for k, v in o.items():
                l.append(f'{indent}"{k}": ' +
                         encode2js(v, _level=_level+1))
            return "{\n%s\n%s}" % (',\n'.join(l), indent)
    elif isinstance(o, (tuple, set, list)):
        assert _level != 0
        if _level == 1:
            return '[\n%s\n]' % ',\n'.join(dumps(v) for v in o)
        else:
            return dumps(o)
    else:
        return dumps(o)

def keys2int(d):
    return {(int(k) if k.isdecimal() else k): v for k, v in d.items()}

def decodejs(js):
    d = loads(js, object_hook=keys2int)
    new_d = {}
    # Strip '-' from keys and convert them to lower case.
    for key in d:
        new_d[key.strip('-').lower()] = d[key]
    d = {}
    # Students ID must be strings.
    for key in new_d['ids']:
        d[str(key)] = new_d['ids'][key]
    new_d['ids'] = d
    return new_d


def dump(path, cfg):
    "Dump `cfg` dict to `path` as json."
    with open(path, 'w') as f:
        f.write(encode2js(cfg, fmt=fmt))

def load(path):
    "Load `path` configuration file (json) and return a dict."
    with open(path) as f:
        js = f.read()
    return decodejs(js)


def real2apparent(q, a, config, ID):
    """Return apparent question number and answer number.

    If `a` is None, return only question number.

    By "apparent", it means question and answer numbers as they
    will appear in the PDF file, after shuffling questions and answers.

    Arguments `q` and `a` are real question and answer numbers, that is
    the ones before questions and answers were shuffled."""
    questions = config['ordering'][ID]['questions']
    answers = config['ordering'][ID]['answers']
    # Apparent question number (ie. after shuffling).
    # Attention, list index 0 correspond to first question is numbered 1, corresponding to .
    q1 = questions.index(q) + 1
    if a is None:
        return q1
    a1 = answers[q].index(a) + 1
    return (q1, a1)


def apparent2real(q, a, config, ID):
    """Return real question number and answer number.

    If `a` is None, return only question number.
    """
    questions = config['ordering'][ID]['questions']
    answers = config['ordering'][ID]['answers']
    # Real question number (ie. before shuffling).
    # Attention, first question is numbered 1, corresponding to list index 0.
    q1 = questions[q - 1]
    if a is None:
        return q1
    # Real answer number (ie. before shuffling).
    a1 = answers[q1][a - 1]
    return (q1, a1)



def correct_answers(config, ID):
    'Return a dict containing the set of the correct answers for each question for test `ID`.'

    questions = config['ordering'][ID]['questions']
    answers = config['ordering'][ID]['answers']
    correct_answers = {}
    for i, q in enumerate(questions):
        # i + 1 is the 'apparent' question number.
        # q is the 'real' question number, ie. the question number before shuffling.
        corr = correct_answers[i + 1] = set()
        for j, a in enumerate(answers[q]):
            # j + 1 is the 'apparent' answer number.
            # a is the 'real' answer number, ie. the answer number before shuffling.
            if a in config['correct_answers'][q]:
                corr.add(j + 1)
    return correct_answers

