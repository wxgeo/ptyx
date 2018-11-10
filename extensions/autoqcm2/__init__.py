"""
AutoQCM

This extension enables computer corrected tests.

An example:

    #LOAD{autoqcm}
    #SEED{8737545887}

    ===========================
    sty=my_custom_sty_file
    scores=1 0 0
    mode=all
    ids=~/my_students.csv
    ===========================


    <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

    ======= Mathematics ===========

    * 1+1 =
    - 1
    + 2
    - 3
    - 4

    - an other answer

    ======= Litterature ==========

    * "to be or not to be", but who actually wrote that ?
    + W. Shakespeare
    - I. Newton
    - W. Churchill
    - Queen Victoria
    - Some bloody idiot

    * Jean de la Fontaine was a famous french
    - pop singer
    - dancer
    + writer
    - detective
    - cheese maker

    > his son is also famous for
    @{\color{blue}%s}
    - dancing french cancan
    - conquering Honolulu
    - walking for the first time on the moon
    - having breakfast at Tiffany

    + none of the above is correct

    >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>


One may include some PTYX code of course.

    """

#TODO: support things like `#NEW INT(2,10) a, b, c, d WITH a*b - c*d != 0`.

from functools import partial
from os.path import join, basename, dirname

from .generate import generate_ptyx_code
from .header import packages_and_macros, ID_band, extract_ID_NAME_from_csv, \
                    extract_NAME_from_csv, student_ID_table, \
                    students_checkboxes
from .config_parser import dump
from .. import extended_python
import randfunc
from utilities import print_sympy_expr

def test_singularity_and_append(code, l, question):
    _code_ = code.strip()
    if _code_ in l:
        msg= [
        'ERROR: Same answer proposed twice in MCQ !',
        'Answer "%s" appeared at least twice for the same question.' % _code_,
        'Question was:',
        repr(question),
        '',
        'Nota: if this is really desired behaviour, insert',
        'following lines in the header of the ptyx file:',
        '#PYTHON',
        'ALLOW_SAME_ANSWER_TWICE=True',
        '#END',
        ]
        n = max(len(s) for s in msg)
        stars = (n + 4)*'*'
        print(stars)
        for s in msg:
            print('* ' + s)
        print(stars)
        raise RuntimeError('Same answer proposed twice in MCQ '
                           '(see message above for more information) !')
    else:
        l.append(_code_)
    return code


# ------------------
#    CUSTOM TAGS
# ------------------

def _parse_QCM_tag(self, node):
    # ~ self.autoqcm_correct_answers = []
    self.autoqcm_data['ordering'][self.NUM] = {'questions': [], 'answers': {}}
#    self.autoqcm_data['answers'] = {}
    # ~ self.autoqcm_data['question_num'] =
    self._parse_children(node.children)

def _parse_ANSWERS_BLOCK_tag(self, node):
    self.write('\n\n\\begin{minipage}{\\textwidth}\n\\begin{flushleft}')
    self._parse_children(node.children)
    self.write('\n\\end{flushleft}\n\\end{minipage}')

def _parse_END_QCM_tag(self, node):
    pass


def _parse_NEW_QUESTION_tag(self, node):
    n = int(node.arg(0))
    self.autoqcm_question_number = n
    # This list is used to test that the same answer is not proposed twice.
    self.auto_qcm_answers = []
    data = self.autoqcm_data['ordering'][self.NUM]
    data['questions'].append(n)
    data['answers'][n] = []
    self.context['APPLY_TO_ANSWERS'] = None
    # This is used to improve message error when an error occured.
    self.current_question = l = []
    def remember_last_question(code, l):
        l.append(code)
        return code
    self._parse_children(node.children[1:], function=partial(remember_last_question, l=l))


def _parse_NEW_ANSWER_tag(self, node):
    k = int(node.arg(0))
    n = self.autoqcm_question_number
    data = self.autoqcm_data['ordering'][self.NUM]
    data['answers'][n].append(k)
    _open_answer(self, n, k)


def _parse_PROPOSED_ANSWER_tag(self, node):
    # TODO: functions should be compiled only once for each question block,
    # not for every answer (though it is probably not be a bottleneck in
    # code execution).
    apply = self.context.get('APPLY_TO_ANSWERS')
    f = None
    if apply:
        # Apply template or function to every answer.
        # Support:
        # - string templates. Ex: \texttt{%s}
        # - functions to apply. Ex: f
        if '%s' in apply:
            f = (lambda s: (apply % s))
        else:
            #~ for key in sorted(self.context):
                #~ print ('* ' + repr(key))
            f = self.context[apply]

    func = f

    if not self.context.get('ALLOW_SAME_ANSWER_TWICE'):
        # This function is used to verify that each answer is unique.
        # This avoids proposing twice the same answer by mistake, which
        # may occur easily when using random values.
        func = g = partial(test_singularity_and_append, l=self.auto_qcm_answers,
                                        question=self.current_question[0])
        if f is not None:
            # Compose functions. Function f should be applied first,
            # since it is not necessarily injective.
            func = (lambda s: g(f(s)))

    self._parse_children(node.children, function=func)
    _close_answer(self)


def _open_answer(self, n, k):
    # `n` is question number *before* shuffling
    # `k` is answer number *before* shuffling
    # When the pdf with solutions will be generated, incorrect answers
    # will be preceded by a white square, while correct ones will
    # be preceded by a gray one.
    is_correct = (k in self.autoqcm_data['correct_answers'][n])
    self.write(r'\AutoQCMTab{')
    cb_id = f'Q{n}-{k}'
    if self.context.get('WITH_ANSWERS') and not is_correct:
        self.write(r'\checkBox{white}{%s}' % cb_id)
    else:
        self.write(r'\checkBox{gray}{%s}' % cb_id)
    self.write(r'}{')


def _close_answer(self):
    # Close 'AutoQCMTab{' written by `_parse_NEW_ANSWER_tag()`.
    self.write(r'}\quad%' '\n')




# Following tag is used to generates the answers from a python list.

def _parse_L_ANSWERS_tag(self, node):
    """#L_ANSWERS{list}{correct_answer} generate answers from a python list.

    Example:
    #L_ANSWERS{l}{l[0]}
    Note that if list or correct_answer are not strings, they will be
    converted automatically to math mode latex code (1/2 -> '$\frac{1}{2}$').
    """
    raw_l = self.context[node.arg(0).strip()]
    def conv(v):
        if isinstance(v, str):
            return v
        return '$%s$' % print_sympy_expr(v)
    correct_answer = conv(eval(node.arg(1).strip(), self.context))

    # Test that first argument seems correct
    # (it must be a list of unique answers including the correct one).
    if not isinstance(raw_l, (list, tuple)):
        raise RuntimeError('#L_ANSWERS: first argument must be a list of answers.')
    l = []
    for v in raw_l:
        test_singularity_and_append(conv(v), l, self.current_question[0])
    if correct_answer not in l:
        raise RuntimeError('#L_ANSWERS: correct answer is not in proposed answers list !')

    # Shuffle and generate LaTeX.
    randfunc.shuffle(l)
    self.write('\n\n' r'\begin{minipage}{\textwidth}' '\n')
    n = self.autoqcm_question_number
    # We will now attribute a unique number to each question.
    # Order don't really matter, but number `1` is reserved to correct answer.
    # Some explanations:
    # In current implementation, correct answer number for each question
    # before shuffling is encoded in a JSON parameter file, as well as
    # the permutation used for each version.
    # This JSON file whill be used by `scan.py` script when scanning students tests later.
    # However, when using a L_ANSWERS tag, questions list is dynamically generated
    # for each version of the document. So we c'ant be sure every version of
    # the list will have the same size. However, this list can't be empty,
    # so there will always be a first question.
    # So, we can manage to have correct answer labeled `1` for every test quite easily.
    # Since `1` is reserved, let's start at `2`.
    i = 2
    for ans in l:
        if ans == correct_answer:
            _open_answer(self, n, 1)
        else:
            _open_answer(self, n, i)
            i += 1
        self.write(ans)
        _close_answer(self)
    self.write('\n\n\\end{minipage}')


def _parse_DEBUG_AUTOQCM_tag(self, node):
    ans = self.autoqcm_correct_answers
    print('---------------------------------------------------------------')
    print('AutoQCM answers:')
    print(ans)
    print('---------------------------------------------------------------')
    self.write(ans)


def _parse_QCM_HEADER_tag(self, node):
    """Parse HEADER.

    HEADER raw format is the following:
    ===========================
    sty=my_custom_sty_file
    scores=1 0 0
    mode=all
    ids=~/my_students.csv
    ===========================
    """
    sty = ''
    WITH_ANSWERS = self.context.get('WITH_ANSWERS')
    if WITH_ANSWERS:
        self.context['format_ask'] = (lambda s: '')
    try:
        check_id_or_name = self.autoqcm_cache['check_id_or_name']
    except KeyError:
        code = ''
        # Read config
        for line in node.arg(0).split('\n'):
            if not line.strip():
                continue
            key, val = line.split('=', maxsplit=1)
            key = key.strip()
            val = val.strip()

            if key in ('scores', 'score'):
                # Set how many points are won/lost for a correct/incorrect answer.
                if ',' in val:
                    vals = val.split(',')
                else:
                    vals = val.split()
                vals = sorted(vals, key=float)
                self.autoqcm_data['correct']['default'] = vals[-1]
                assert 1 <= len(vals) <= 3, 'One must provide between 1 and 3 scores '\
                        '(for correct answers, incorrect answers and no answer at all).'
                if len(vals) >= 2:
                    self.autoqcm_data['incorrect']['default'] = vals[0]
                    if len(vals) >= 3:
                        self.autoqcm_data['skipped']['default'] = vals[1]

            elif key == 'mode':
                self.autoqcm_data['mode']['default'] = val

            elif key in ('names', 'name', 'students', 'student') and not WITH_ANSWERS:
                # val must be the path of a CSV file.
                students = extract_NAME_from_csv(val, self.compiler.state['path'])
                code  = students_checkboxes(students)
                self.autoqcm_data['students_list'] = students

            elif key in ('id', 'ids') and not WITH_ANSWERS:
                # val must be the path of a CSV file.
                ids = extract_ID_NAME_from_csv(val, self.compiler.state['path'])
                code = student_ID_table(ids)
                self.autoqcm_data['ids'] = ids

            elif key in ('sty', 'package'):
                sty = val

        check_id_or_name = (code if not self.context.get('WITH_ANSWERS') else '')
        self.autoqcm_cache['check_id_or_name'] = check_id_or_name
        check_id_or_name += r'''
        \vspace{1em}

        \tikz{\draw[dotted] ([xshift=2cm]current page.west) -- (current page.east);}
        '''

    try:
        header = self.autoqcm_cache['header']
    except KeyError:
        # TODO: Once using Python 3.6+ (string literals),
        # make packages_and_macros() return a tuple
        # (it's to painful for now because of.format()).
        if sty:
            sty = r'\usepackage{%s}' % sty
        header1, header2 = packages_and_macros()
        header = '\n'.join([header1, sty, header2, r'\begin{document}'])
        self.autoqcm_cache['header'] = header

    # Generate barcode
    # Barcode must NOT be put in the cache, since each document has a
    # unique ID.
    n = self.context['NUM']
    calibration=('AUTOQCM__SCORE_FOR_THIS_STUDENT' not in self.context)
    barcode = ID_band(ID=n, calibration=calibration)

    self.write('\n'.join([header, barcode, check_id_or_name]))






def main(text, compiler):
    # Generation algorithm is the following:
    # 1. Parse AutoQCM code, to convert it to plain pTyX code.
    #    Doing this, we now know the number of questions, the number
    #    of answers per question and the students names.
    #    However, we can't know for know the number of the correct answer for
    #    each question, since questions numbers and answers numbers too will
    #    change during shuffling, when compiling pTyX code (and keeping track of
    #    them through shuffling is not so easy).
    # 2. Generate syntax tree, and then compile pTyX code many times to generate
    #    one test for each student. For each compilation, keep track of correct
    #    answers.
    #    All those data are stored in `latex_generator.autoqcm_data['answers']`.
    #    `latex_generator.autoqcm_data['answers']` is a dict
    #    with the following structure:
    #    {1:  [          <-- test n°1 (test id is stored in NUM)
    #         [0,3,5],   <-- 1st question: list of correct answers
    #         [2],       <-- 2nd question: list of correct answers
    #         [1,5],     ...
    #         ],
    #     2:  [          <-- test n°2
    #         [2,3,4],   <-- 1st question: list of correct answers
    #         [0],       <-- 2nd question: list of correct answers
    #         [1,2],     ...
    #         ],
    #    }
    text = extended_python.main(text, compiler)
    # For efficiency, update only for last tag.
    compiler.add_new_tag('QCM', (0, 0, ['END_QCM']), _parse_QCM_tag, 'autoqcm', update=False)
    compiler.add_new_tag('NEW_QUESTION', (1, 0, ['@END', '@END_QUESTION']), _parse_NEW_QUESTION_tag, 'autoqcm', update=False)
    compiler.add_new_tag('NEW_ANSWER', (1, 0, None), _parse_NEW_ANSWER_tag, 'autoqcm', update=False)
    compiler.add_new_tag('END_QCM', (0, 0, None), _parse_END_QCM_tag, 'autoqcm', update=False)
    compiler.add_new_tag('QCM_HEADER', (1, 0, None), _parse_QCM_HEADER_tag, 'autoqcm', update=False)
    compiler.add_new_tag('PROPOSED_ANSWER', (0, 0, ['@END']), _parse_PROPOSED_ANSWER_tag, 'autoqcm', update=False)
    compiler.add_new_tag('ANSWERS_BLOCK', (0, 0, ['@END']), _parse_ANSWERS_BLOCK_tag, 'autoqcm', update=False)
    compiler.add_new_tag('L_ANSWERS', (2, 0, None), _parse_L_ANSWERS_tag, 'autoqcm', update=False)
    compiler.add_new_tag('DEBUG_AUTOQCM', (0, 0, None), _parse_DEBUG_AUTOQCM_tag, 'autoqcm', update=True)
    code, correct_answers = generate_ptyx_code(text)
    # Some tags use cache, for code which don't change between two successive compilation.
    # (Typically, this is used for (most of) the header).
    compiler.latex_generator.autoqcm_cache = {}
    # Default configuration:
    compiler.latex_generator.autoqcm_data = {
            'mode': {'default': 'some'},
            'correct': {'default': 1},
            'incorrect': {'default': 0},
            'skipped': {'default': 0},
            'correct_answers': correct_answers, # {1: [4], 2:[1,5], ...}
            'students': [],
            'id-table-pos': None,
            'ids': {},
            'ordering': {}, # {NUM: {'questions': [2,1,3...], 'answers': {1: [2,1,3...], ...}}, ...}
            'boxes': {}, # {NUM: {'tag': 'p4, (23.456, 34.667)', ...}, ...}
            }
    assert isinstance(code, str)
    return code


def close(compiler):
    autoqcm_data = compiler.latex_generator.autoqcm_data
    path = compiler.state['path']
    folder = dirname(path)
    name = basename(path)
    id_table_pos = None
    for n in autoqcm_data['ordering']:
        # XXX: what if files are not auto-numbered, but a list
        # of names is provided to Ptyx instead ?
        # (cf. command line options).
        if len(autoqcm_data['ordering']) == 1:
            filename = f'{name[:-5]}.pos'
        else:
            filename = f'{name[:-5]}-{n}.pos'
        full_path = join(folder, '.compile', name, filename)
        d = autoqcm_data['boxes'][n] = {}
        with open(full_path) as f:
            for line in f:
                k, v = line.split(': ', 1)
                k = k.strip()
                if k == 'ID-table':
                    if id_table_pos is None:
                        id_table_pos = [float(s.strip('() \n')) for s in v.split(',')]
                        autoqcm_data['id-table-pos'] = id_table_pos
                    continue
                page, x, y = [s.strip('p() \n') for s in v.split(',')]
                d.setdefault(page, {})[k] = [float(x), float(y)]


    config_file = path + '.autoqcm.config.json'
    dump(config_file, autoqcm_data)

