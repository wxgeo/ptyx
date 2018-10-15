import re


def read_config(pth):
    def bool_(s):
        return s.lower() == 'true'
    cfg = {'answers': {}, 'students': [], 'ids': {}, 'boxes': {}}
    parameters_types = {'mode': str, 'correct': float, 'incorrect': float,
                  'skipped': float, 'questions': int, 'answers (max)': int,
                  'flip': bool_, 'seed': int}
    ans = cfg['answers']
    boxes = cfg['boxes']
    REG = re.compile(r'Q(?P<question>[0-9]+)-(?P<answer>[0-9]+) '
            r'\((?P<bool>False|True)\): page (?P<page>[0-9]+), '
            r'position \((?P<x>[0-9.]+), (?P<y>[0-9.]+)\)')
    with open(pth) as f:
        section = 'parameters'
        for line in f:
            if not line.strip():
                continue
            try:
                if line.startswith('*** ANSWERS (TEST '):
                    num = int(line[18:-6])
                    ans[num] = []
                    section = 'answers'
                elif line.startswith('*** BOXES (TEST '):
                    num = int(line[16:-6])
                    boxes[num] = {}
                    section = 'boxes'
                elif line.startswith('*** STUDENTS LIST ***'):
                    section = 'students'
                    students = cfg['students']
                elif line.startswith('*** IDS LIST ***'):
                    section = 'ids'
                    ids = cfg['ids']
                else:
                    if section == 'parameters':
                        key, val =  line.split(':')
                        key = key.strip().lower()
                        val = parameters_types[key](val.strip())
                        cfg[key] = val
                    elif section == 'answers':
                        q, correct_ans = line.split(' -> ')
                        # There may be no answers, so test if string is empty.
                        if correct_ans.strip():
                            ans[num].append([int(n) - 1 for n in correct_ans.split(',')])
                        else:
                            ans[num].append([])
                        assert len(ans[num]) == int(q), (f'Incorrect question number: {q}')
                    elif section == 'boxes':
                        if line.startswith('ID-table:'):
                            cfg['ID-table-pos'] = tuple(float(val) for val
                                                        in line[11:-2].split(','))
                            continue
                        try:
                            g = REG.match(line).group
                        except AttributeError:
                            raise ValueError(f'Error at line {repr(line)}')
                        boxes[num].setdefault(int(g('page')), {}) \
                                  .setdefault(g('question'), {}) \
                                  [g('answer')] = {'correct': bool_(g('bool')),
                                                   'pos': (float(g('x')), float(g('y')))}
                    elif section == 'students':
                        students.append(line.strip())
                    elif section == 'ids':
                        ID, name = line.split(':', 1)
                        ids[ID.strip()] = name.strip()
                    else:
                        raise NotImplementedError('Unknown section: %s !' % section)

            except Exception:
                print("Error while parsing this line: " + repr(line))
                raise
    return cfg
