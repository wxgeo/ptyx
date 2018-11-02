from json import loads, dumps as _dumps

def dumps(o):
    return _dumps(o, ensure_ascii=False)

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
            return dumps(o)
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

