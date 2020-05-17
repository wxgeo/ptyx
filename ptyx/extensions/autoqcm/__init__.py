"""
AutoQCM

This extension enables computer corrected quizzes.

An example:

    #LOAD{autoqcm2}
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

#TODO: support things like `#NEW INT(2,10) a, b, c, d WITH a*b - c*d != 0` ?

from functools import partial
from os.path import join, basename, dirname

from ptyx.extensions import extended_python
import ptyx.randfunc as randfunc
from ptyx.utilities import print_sympy_expr

from .compile.generate import generate_ptyx_code
from .compile.header import packages_and_macros, ID_band, extract_ID_NAME_from_csv, \
                    extract_NAME_from_csv, student_ID_table, \
                    students_checkboxes, IdentifiantError
from .tools.config_parser import dump


def test_singularity_and_append(code, l, question):
    code = code.strip()
    if code in l:
        msg= [
        'ERROR: Same answer proposed twice in MCQ !',
        f'Answer {code!r} appeared at least twice for the same question.',
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
        l.append(code)
    return code


# ------------------
#    CUSTOM TAGS
# ------------------

def has_option(node, option):
    return option in [opt.strip() for opt in node.options.split(',')]

def _parse_QCM_tag(self, node):
    # ~ self.autoqcm_correct_answers = []
    self.autoqcm_data['ordering'][self.NUM] = {'questions': [], 'answers': {}}
#    self.autoqcm_data['answers'] = {}
    # ~ self.autoqcm_data['question_num'] =
    if has_option(node, 'shuffle') :
        self._shuffle_and_parse_children(node, target='SECTION')
    else:
        self._parse_children(node.children)


def _parse_SECTION_tag(self, node):
    title = (node.options.strip() if node.options else '')
    if title:
        self.write(r'\section{%s}' % title)
    children = node.children
    # Nota: \begin{enumerate} must not be written just after the
    # beginning of the section, since there may be some explanations
    # between the section title and the first question.
    # So, we have to insert it just before the first NEW_QUESTION.
    try:
        i = self._child_index(children, 'NEW_QUESTION')
    except ValueError:
        self._parse_children(children)
        return
    self._parse_children(children[:i])
    self.write(r'\begin{enumerate}[resume]')
    self._shuffle_and_parse_children(node, children[i:], target='NEW_QUESTION')
    self.write(r'\end{enumerate}')

#
#def _parse_QUESTIONS_BLOCK_tag(self, node):
#    shuffle = has_option(node, 'shuffle')
#    if shuffle:
#        self._shuffle_children(node, target='NEW_QUESTION')


def _parse_NEW_QUESTION_tag(self, node):
    self._pick_and_parse_children(node, children=node.children,
                                  target='VERSION',
                                  )


# Same function, but name must be different so that shuffling does not apply.
_parse_CONSECUTIVE_QUESTION_tag = _parse_NEW_QUESTION_tag


def _parse_VERSION_tag(self, node):
    n = int(node.arg(0))
    self.autoqcm_question_number = n
    # This list is used to test that the same answer is not proposed twice.
    self.autoqcm_answers = []
    data = self.autoqcm_data['ordering'][self.NUM]
    data['questions'].append(n)
    data['answers'][n] = []
    self.context['APPLY_TO_ANSWERS'] = None
    self.context['RAW_CODE'] = None
    self.write(r'\pagebreak[3]\item\filbreak')
    self.write(r'\setcounter{answerNumber}{0}')
    # This is used to improve message error when an error occured.
    self.current_question = l = []
    # The question itself is stored to make debuging easier (error messages will
    # display current question).
    def remember_last_question(code, l):
        l.append(code)
        return code
    # So, we have to find where the question itself ends and the answers start.
    try:
        i = self._child_index(node.children, 'ANSWERS_BLOCK')
    except ValueError:
        i = self._child_index(node.children, 'L_ANSWERS')
    self._parse_children(node.children[1:i],
                         function=partial(remember_last_question, l=l),
                         )
    # This is the end of the question itself.

    # And then, the answers follow.
    self.write('\n\\nopagebreak[4]\n')
    self.write('\n\\begin{minipage}{\\textwidth}\n\\begin{flushleft}')
    self._parse_children(node.children[i:])
    self.write('\\end{flushleft}\n\\end{minipage}')


def _parse_ANSWERS_BLOCK_tag(self, node):
    self._shuffle_and_parse_children(node, target='NEW_ANSWER')


def _parse_NEW_ANSWER_tag(self, node):
    k = int(node.arg(0))
    n = self.autoqcm_question_number
    data = self.autoqcm_data['ordering'][self.NUM]
    data['answers'][n].append(k)
    _open_answer(self, n, k)
    # Functions to apply. Last one is applied first:
    # if functions = [f, g, h], then s -> f(g(h(s))).
    functions = []

    # TODO(?): functions should be compiled only once for each question block,
    # not for every answer (though it is probably not be a bottleneck in
    # code execution).
    apply = self.context.get('APPLY_TO_ANSWERS')
    if apply:
        # Apply template or function to every answer.
        # Support:
        # - string templates. Ex: \texttt{%s}
        # - name of the function to apply. Ex: f.
        # In last case, the function must have been defined or imported
        # before.
        if '%s' in apply:
            functions.append(lambda s: (apply % s))
        else:
            # Search for the function name in context.
            functions.append(self.context[apply])

    if self.context.get('RAW_CODE'):
        # Try to emulate verbatim (which is not allowed inside
        # a macro argument in LaTeX).
        def escape(s):
            # Replace \ first !
            s = s.replace('\\', r'\textbackslash<!ø5P3C14Lø?>')
            s = s.replace('~', r'\textasciitilde<!ø5P3C14Lø?>')
            s = s.replace('^', r'\textasciicircum<!ø5P3C14Lø?>')
            s = s.replace("'", r'\textquotesingle<!ø5P3C14Lø?>')
            for char in '#$%&_{}':
                s = s.replace(char, fr'\{char}')
            s = s.replace('<!ø5P3C14Lø?>', '{}')
            return fr'\texttt{{{s}}}'
        functions.append(escape)

    if not self.context.get('ALLOW_SAME_ANSWER_TWICE'):
        # This function is used to verify that each answer is unique.
        # This avoids proposing twice the same answer by mistake, which
        # may occur easily when using random values.
        functions.append(partial(test_singularity_and_append, l=self.autoqcm_answers,
                                        question=self.current_question[0]))

    self._parse_children(node.children[1:], function=functions)
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
    if self.context.get('WITH_ANSWERS') and is_correct:
        self.write(r'\checkBox{gray}{%s}' % cb_id)
    else:
        self.write(r'\checkBox{white}{%s}' % cb_id)
    self.write(r'}{')


def _close_answer(self):
    # Close 'AutoQCMTab{' written by `_parse_NEW_ANSWER_tag()`.
    self.write(r'}\quad' '\n')




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
    data = self.autoqcm_data['ordering'][self.NUM]
    # We will now attribute a unique number to each question.
    # Order don't really matter, but number `1` is reserved to correct answer.
    # Some explanations:
    # In current implementation, correct answer number for each question
    # before shuffling is encoded in a JSON parameter file, as well as
    # the permutation used for each version.
    # This JSON file whill be used by `scan.py` script when scanning students tests later.
    # However, when using a L_ANSWERS tag, questions list is dynamically generated
    # for each version of the document. So we can't be sure that every version of
    # the list will have the same size. However, this list can't be empty,
    # so there will always be a first question.
    # So, we can manage to have correct answer labeled `1` for every test quite easily.
    # Since `1` is reserved, let's start at `2`.
    i = 2
    for ans in l:
        if ans == correct_answer:
            k = 1
        else:
            k = i
            i += 1
        _open_answer(self, n, k)
        data['answers'][n].append(k)
        self.write(ans)
        _close_answer(self)
    self.write('\n\n\\end{minipage}')


def _parse_DEBUG_AUTOQCM_tag(self, node):
    data = self.autoqcm_data
    print('---------------------------------------------------------------')
    print('AutoQCM data:')
    print(data)
    print('---------------------------------------------------------------')
    #self.write(data)






def _analyze_IDS(ids):
    """Given a list of IDs (str), return:
    - the length of an ID (or raise an error if they don't have the same size),
    - the maximal number of different digits in an ID caracter,
    - a list of sets corresponding to the different digits used for each ID caracter.

    >>> _analyze_IDS(['18', '19', '20', '21'])
    (2, 4, [{'1', '2'}, {'8', '9', '0', '1'}])
     """
    lengths = {len(iD) for iD in ids}
    if len(lengths) != 1:
        raise IdentifiantError('All students ID must have the same length !')
    ID_length = lengths.pop()
    # On crée la liste de l'ensemble des valeurs possibles pour chaque chiffre.
    digits = [set() for i in range(ID_length)]
    for iD in ids:
        for i, digit in enumerate(iD):
            digits[i].add(digit)

    max_ndigits = max(len(set_) for set_ in digits)
    return ID_length, max_ndigits, digits


def _detect_ID_format(ids, id_format):
    """Return IDs and ID format data.

    `ids` is a dictionnary who contains students names and ids.
    `id_format` is a string, specifying a number of digits ('8 digits'...).

    Returned ID format data will consist of:
    - the length of an ID,
    - the maximal number of different digits in an ID caracter,
    - a list of sets corresponding to the different digits used for each ID caracter.
    """
    ID_length = None
    if ids:
        # Analyze the IDs list even if `id_format` is provided.
        # This enables to check the consistency between the IDs list and the
        # given ID format.
        ID_length, max_ndigits, digits = _analyze_IDS(ids)

    if id_format:
        n, ext = id_format.split()
        # Test format syntax
        if ext not in ('digit', 'digits'):
            raise ValueError(f'Unknown format : {id_format!r}')
        try:
            n = int(n)
        except ValueError:
            raise ValueError(f'Unknown format : {id_format!r}')
        # Test consistency between format and IDs
        if ID_length is not None and ID_length != n:
            raise IdentifiantError("Identifiants don't match given format !")
        # Generate format data
        ID_length = n
        max_ndigits = 10
        digits = n*[tuple('0123456789')]

    return {'ids': ids, 'id_format': (ID_length, max_ndigits, digits)}


def _parse_QCM_HEADER_tag(self, node):
    """Parse HEADER.

    HEADER raw format is the following:
    ===========================
    sty=my_custom_sty_file
    scores=1 0 0
    mode=all
    ids=~/my_students_ids_and_names.csv
    names=~/my_students_names.csv
    id_format=8 digits
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

        def format_key(key):
            return key.strip().replace(' ', '_').lower()
        # {alias: standard key name}
        alias = {'score': 'scores',
                 'name': 'names',
                 'student': 'names',
                 'students': 'names',
                 'id': 'ids',
                 'package': 'sty',
                 'packages': 'sty',
                 'id_formats': 'id_format',
                 'ids_formats': 'id_format',
                 'ids_format': 'id_format',
                 }
        # Read config
        config = {}
        for line in node.arg(0).split('\n'):
            if '=' not in line:
                continue
            key, val = line.split('=', maxsplit=1)
            # Normalize key.
            key = format_key(key)
            key = alias.get(key, key)
            config[key] = val.strip()


        if 'scores' in config:
            # Set how many points are won/lost for a correct/incorrect answer.
            val = config.pop('scores').replace(',', ' ')
            # A correct answer should always give more points than an incorrect one !
            vals = sorted(val.split(), key=float)
            self.autoqcm_data['correct']['default'] = vals[-1]
            if len(vals) > 3:
                raise ValueError('`scores` should provide 3 values at most '\
                        '(correct answer / incorrect answer / no answer).')
            if len(vals) >= 2:
                self.autoqcm_data['incorrect']['default'] = vals[0]
                if len(vals) >= 3:
                    self.autoqcm_data['skipped']['default'] = vals[1]

        if 'mode' in config:
            self.autoqcm_data['mode']['default'] = config.pop('mode')

        if 'names' in config:
            # the value must be the path of a CSV file.
            csv = config.pop('names')
            if not WITH_ANSWERS:
                students = extract_NAME_from_csv(csv, self.compiler.state['path'])
                code  = students_checkboxes(students)
                self.autoqcm_data['students_list'] = students

        if 'ids' in config or 'id_format' in config:
            # config['ids'] must be the path of a CSV file.
            csv = config.pop('ids', None)
            id_format = config.pop('id_format', None)

            if not WITH_ANSWERS:
                if csv:
                    ids = extract_ID_NAME_from_csv(csv, self.compiler.state['path'])
                else:
                    ids=None

                try:
                    data = _detect_ID_format(ids, id_format)
                except IdentifiantError as e:
                    msg = e.args[0]
                    raise IdentifiantError(f'Error in {csv!r} : {msg!r}')

                self.autoqcm_data.update(data)
                code = student_ID_table(*data['id_format'])

        if 'sty' in config:
            sty = config.pop('sty')


        # Config should be empty by now !
        for key in config:
            raise NameError(f'Unknown key {key!r} in the header of the pTyX file.')

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

    # Register custom tags and corresponding handlers for this extension.
    new_tag = partial(compiler.add_new_tag, extension_name='autoqcm')

    # Note for closing tags:
    # '@END' means closing tag #END must be consumed, unlike 'END'.
    # So, use '@END_QUESTIONS_BLOCK' to close QUESTIONS_BLOCK,
    # but use 'END_QUESTIONS_BLOCK' to close QUESTION, since
    # #END_QUESTIONS_BLOCK must not be consumed then (it must close
    # QUESTIONS_BLOCK too).

    # Tags used to structure MCQ
    new_tag('QCM', (0, 0, ['@END_QCM']), _parse_QCM_tag)
    new_tag('SECTION', (0, 0, ['SECTION', 'END_QCM']), _parse_SECTION_tag)
    new_tag('NEW_QUESTION', (0, 0, ['NEW_QUESTION', 'CONSECUTIVE_QUESTION',
                                    'SECTION', 'END_QCM']),
            _parse_NEW_QUESTION_tag)
    new_tag('CONSECUTIVE_QUESTION', (0, 0, ['NEW_QUESTION', 'CONSECUTIVE_QUESTION',
                                            'SECTION', 'END_QCM']),
            _parse_NEW_QUESTION_tag)
    new_tag('VERSION', (1, 0, ['VERSION', 'NEW_QUESTION', 'CONSECUTIVE_QUESTION',
                                    'SECTION', 'END_QCM']), _parse_VERSION_tag)
    new_tag('ANSWERS_BLOCK', (0, 0, ['@END_ANSWERS_BLOCK']),
            _parse_ANSWERS_BLOCK_tag)
    new_tag('NEW_ANSWER', (1, 0, ['NEW_ANSWER', 'END_ANSWERS_BLOCK']),
            _parse_NEW_ANSWER_tag)
    new_tag('L_ANSWERS', (2, 0, None), _parse_L_ANSWERS_tag)

    # Other tags
    new_tag('QCM_HEADER', (1, 0, None), _parse_QCM_HEADER_tag)
    new_tag('DEBUG_AUTOQCM', (0, 0, None), _parse_DEBUG_AUTOQCM_tag)

    # For efficiency, update only once, after last tag is added.
    compiler.update_tags_info()
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
            'id_format': None,
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

