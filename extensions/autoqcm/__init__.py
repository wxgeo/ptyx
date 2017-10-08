"""
AutoQCM

This extension enables computer corrected tests.

An example:

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
    - dancing french cancan
    - conquering Honolulu
    - walking for the first time on the moon
    - having breakfast at Tiffany

    + none of the above is correct

    >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>


One may include some PTYX code of course.

#NEW INT(2,10) a, b, c, d WITH a*b - c*d != 0


    """

from functools import partial

from .generate import (generate_tex, generate_identification_band,
                       generate_table_for_answers)
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


class AutoQCMTags(object):
    def _parse_QCM_tag(self, node):
        self.autoqcm_correct_answers = []
        self.n_questions = 0
        self.n_max_answers = 0
        self._parse_children(node.children)

    def _parse_ANSWERS_BLOCK_tag(self, node):
        self.write('\n\n\\begin{minipage}{\\textwidth}\n\\begin{flushleft}')
        self._parse_children(node.children)
        self.write('\n\\end{flushleft}\n\\end{minipage}')

    def _parse_END_QCM_tag(self, node):
        data = self.autoqcm_data
        context = self.context
        n = context['NUM']
        data['answers'][n] = self.autoqcm_correct_answers
        # Those are supposed to have same value for each test,
        # so we don't save test number:
        data['n_questions'] = len(self.autoqcm_correct_answers)
        data['n_max_answers'] = self.n_max_answers

        # Now, we know the number of questions and of answers per question for
        # the whole MCQ, so we can generate the table for the answers.
        args, kw = data['table_for_answers_options']
        kw['answers'] = int(kw.get('answers', data['n_max_answers']))
        kw['questions'] = int(kw.get('questions', data['n_questions']))
        if context.get('WITH_ANSWERS'):
            kw['correct_answers'] = data['answers'][n]
        latex = generate_table_for_answers(*args, **kw)
        # orientation must be stored for scan later.
        data['flip'] = bool(kw.get('flip', False))
        #XXX: If flip is not the same for all tests, only last flip value
        # will be stored, which may lead to errors (though it's highly unlikely
        # that user would adapt flip value depending on subject number).

        # Search backward for #TABLE_FOR_ANSWERS to replace it with
        # corresponding LaTeX code.
        for textlist in self.backups + [self.context['LATEX']]:
            for i, elt in enumerate(reversed(textlist)):
                if elt == '#TABLE_FOR_ANSWERS':
                    textlist[len(textlist) - i - 1] = latex

    def _parse_SCORES_tag(self, node):
        arg = node.arg(0)
        vals = sorted(arg.split(), key=float)
        self.autoqcm_data['correct'] = vals[-1]
        assert 1 <= len(vals) <= 3, 'One must provide between 1 and 3 scores '\
                '(for correct answers, incorrect answers and no answer at all).'
        if len(vals) >= 2:
            self.autoqcm_data['incorrect'] = vals[0]
            if len(vals) >= 3:
                self.autoqcm_data['skipped'] = vals[1]

    def _parse_NEW_QUESTION_tag(self, node):
        self.autoqcm_correct_answers.append([])
        self.autoqcm_answer_number = 0
        self.auto_qcm_answers = []
        # This is used to improve message error when an error occured.
        self.current_question = l = []
        def remember_last_question(code, l):
            l.append(code)
            return code
        self._parse_children(node.children, function=partial(remember_last_question, l=l))


    def _parse_AUTOQCM_BARCODE_tag(self, node):
        n = self.context['NUM']
        full=('AUTOQCM__SCORE_FOR_THIS_STUDENT' not in self.context)
        self.write(generate_identification_band(identifier=n, full=full))

    def _parse_TABLE_FOR_ANSWERS_tag(self, node):
        self.autoqcm_data['table_for_answers_options'] = self._parse_options(node)
        # Don't parse it now, since we don't know the number of questions
        # and of answers par question for now.
        # Write the tag name as a bookmark... it will be replaced by latex
        # code eventually when closing MCQ (see: _parse_END_QCM_tag).
        self.write('#TABLE_FOR_ANSWERS')


    def _parse_PROPOSED_ANSWER_tag(self, node):
        if self.context.get('ALLOW_SAME_ANSWER_TWICE'):
            f = None
        else:
            f = partial(test_singularity_and_append, l=self.auto_qcm_answers,
                                            question=self.current_question[0])
        self.write(r'\begin{tabular}[t]{l}')
        self._parse_children(node.children, function=f)
        self.write(r'\end{tabular}\quad%' '\n')

    def _parse_NEW_ANSWER_tag(self, node):
        is_correct = (node.arg(0) == 'True')
        # Add counter for each answer.
        self.write(r'\stepcounter{answerNumber}')
        # When the pdf with solutions will be generated, incorrect answers
        # will be preceded by a white square, while correct ones will
        # be preceded by a gray one.
        if self.context.get('WITH_ANSWERS') and not is_correct:
            self.write(r'\whitesquared')
        else:
            self.write(r'\graysquared')
        self.write(r'{\alph{answerNumber}}')
        if is_correct:
            self.autoqcm_correct_answers[-1].append(self.autoqcm_answer_number)
        self.autoqcm_answer_number += 1
        if self.autoqcm_answer_number > self.n_max_answers:
            self.n_max_answers = self.autoqcm_answer_number


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
        self.write('\n\n\\begin{minipage}{\\textwidth}\n\\begin{flushleft}')
        for ans in l:
            is_correct = (ans == correct_answer)
            if is_correct:
                self.autoqcm_correct_answers[-1].append(self.autoqcm_answer_number)
            self.autoqcm_answer_number += 1
            if self.autoqcm_answer_number > self.n_max_answers:
                self.n_max_answers = self.autoqcm_answer_number
            self.write(r'\stepcounter{answerNumber}')
            if self.context.get('WITH_ANSWERS') and not is_correct:
                self.write(r'\whitesquared')
            else:
                self.write(r'\graysquared')
            self.write(r'{\alph{answerNumber}}\begin{tabular}[t]{c}%s\end{tabular}\quad' % ans)
            self.write('%\n')
        self.write('\n\\end{flushleft}\n\\end{minipage}')


    def _parse_DEBUG_AUTOQCM_tag(self, node):
        ans = self.autoqcm_correct_answers
        print('---------------------------------------------------------------')
        print('AutoQCM answers:')
        print(ans)
        print('---------------------------------------------------------------')
        self.write(ans)


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
    compiler.add_new_tag('QCM', (0, 0, ['END_QCM']), AutoQCMTags._parse_QCM_tag, 'autoqcm', update=False)
    compiler.add_new_tag('NEW_QUESTION', (0, 0, ['@END', '@END_QUESTION']), AutoQCMTags._parse_NEW_QUESTION_tag, 'autoqcm', update=False)
    compiler.add_new_tag('NEW_ANSWER', (1, 0, None), AutoQCMTags._parse_NEW_ANSWER_tag, 'autoqcm', update=False)
    compiler.add_new_tag('END_QCM', (0, 0, None), AutoQCMTags._parse_END_QCM_tag, 'autoqcm', update=False)
    compiler.add_new_tag('AUTOQCM_BARCODE', (0, 0, None), AutoQCMTags._parse_AUTOQCM_BARCODE_tag, 'autoqcm', update=False)
    compiler.add_new_tag('TABLE_FOR_ANSWERS', (0, 0, None), AutoQCMTags._parse_TABLE_FOR_ANSWERS_tag, 'autoqcm', update=False)
    compiler.add_new_tag('SCORES', (1, 0, None), AutoQCMTags._parse_SCORES_tag, 'autoqcm', update=False)
    compiler.add_new_tag('PROPOSED_ANSWER', (0, 0, ['@END']), AutoQCMTags._parse_PROPOSED_ANSWER_tag, 'autoqcm', update=False)
    compiler.add_new_tag('ANSWERS_BLOCK', (0, 0, ['@END']), AutoQCMTags._parse_ANSWERS_BLOCK_tag, 'autoqcm', update=False)
    compiler.add_new_tag('L_ANSWERS', (2, 0, None), AutoQCMTags._parse_L_ANSWERS_tag, 'autoqcm', update=False)
    compiler.add_new_tag('DEBUG_AUTOQCM', (0, 0, None), AutoQCMTags._parse_DEBUG_AUTOQCM_tag, 'autoqcm', update=True)
    code, students_list = generate_tex(text)
    compiler.latex_generator.autoqcm_data = {'answers': {},
            'students': students_list,
            'correct': 1,
            'incorrect': 0,
            'skipped': 0,
            'mode': 'some',
            }
    assert isinstance(code, str)
    return code


def close(compiler):
    g = compiler.latex_generator
    answers = sorted(g.autoqcm_data['answers'].items())
    l = []
    l.append('MODE: %s' % g.autoqcm_data['mode'])
    l.append('CORRECT: %s' % g.autoqcm_data['correct'])
    l.append('INCORRECT: %s' % g.autoqcm_data['incorrect'])
    l.append('SKIPPED: %s' % g.autoqcm_data['skipped'])
    l.append('QUESTIONS: %s' % g.autoqcm_data['n_questions'])
    l.append('ANSWERS (MAX): %s' % g.autoqcm_data['n_max_answers'])
    l.append('FLIP: %s' % g.autoqcm_data['flip'])
    l.append('SEED: %s' % compiler.state['seed'])
    for n, correct_answers in answers:
        l.append('*** ANSWERS (TEST %s) ***' % n)
        for i, nums in enumerate(correct_answers):
            # Format: question -> correct answers
            # For example: 1 -> 1,3,4
            l.append('%s -> %s' % (i + 1, ','.join(str(j + 1) for j in nums)))

    l.append('*** STUDENTS LIST ***')
    for name in g.autoqcm_data['students']:
        l.append(name)

    with open(compiler.state['path'] + '.autoqcm.config', 'w') as f:
        f.write('\n'.join(l))


