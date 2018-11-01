from json import loads, dumps as _dumps

def dumps(o):
    return _dumps(o, ensure_ascii=False)

def encode2js(o, _level=0):
    if _level == 0 and not isinstance(o, dict):
        raise NotImplementedError
    if isinstance(o, dict):
        if _level == 0:
            l = []
            for k, v in o.items():
                l.append(f'"{k.upper().center(40,"-")}":\n' +
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
        f.write(encode2js(cfg))

def load(path):
    "Load `path` configuration file (json) and return a dict."
    with open(path) as f:
        js = f.read()
    return decodejs(js)
