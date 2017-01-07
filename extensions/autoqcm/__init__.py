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

from .generate import generate_tex, generate_identification_band
from .. import extended_python


class AutoQCMTags(object):
    def _parse_NEW_QCM_tag(self, node):
        self.autoqcm_correct_answers = []

    def _parse_END_QCM_tag(self, node):
        # TODO: Store QCM with NUM value.
        n = self.context['NUM']
        self.autoqcm_data['answers'][n] = self.autoqcm_correct_answers

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

    def _parse_GRAY_IF_CORRECT_tag(self, node):
        n = self.context['NUM']
        if n in self.autoqcm_data['answers']:
            col = int(node.arg(0))
            line = int(node.arg(1))
            if line in self.autoqcm_data['answers'][n][col]:
                self.write('fill=gray,')

    def _parse_NEW_QUESTION_tag(self, node):
        self.autoqcm_correct_answers.append([])
        self.autoqcm_answer_number = 0

    def _parse_NEW_ANSWER_tag(self, node):
        if (node.arg(0) == 'True'):
            self.autoqcm_correct_answers[-1].append(self.autoqcm_answer_number)
        self.autoqcm_answer_number += 1

    def _parse_AUTOQCM_HEADER_tag(self, node):
        n = self.context['NUM']
        full=('AUTOQCM__SCORE_FOR_THIS_STUDENT' not in self.context)
        self.write(generate_identification_band(identifier=n, full=full))

    def _parse_DEBUG_AUTOQCM_tag(self, node):
        ans = self.autoqcm_correct_answers
        print('---------------------------------------------------------------')
        print('AutoQCM answers:')
        print(ans)
        print('---------------------------------------------------------------')
        self.write(ans)

def main(text, compiler):
    text = extended_python.main(text, compiler)
    # For efficiency, update only for last tag.
    compiler.add_new_tag('NEW_QCM', (0, 0, None), AutoQCMTags._parse_NEW_QCM_tag, 'autoqcm', update=False)
    compiler.add_new_tag('NEW_QUESTION', (0, 0, None), AutoQCMTags._parse_NEW_QUESTION_tag, 'autoqcm', update=False)
    compiler.add_new_tag('NEW_ANSWER', (1, 0, None), AutoQCMTags._parse_NEW_ANSWER_tag, 'autoqcm', update=False)
    compiler.add_new_tag('END_QCM', (0, 0, None), AutoQCMTags._parse_END_QCM_tag, 'autoqcm', update=False)
    compiler.add_new_tag('AUTOQCM_HEADER', (0, 0, None), AutoQCMTags._parse_AUTOQCM_HEADER_tag, 'autoqcm', update=False)
    compiler.add_new_tag('SCORES', (1, 0, None), AutoQCMTags._parse_SCORES_tag, 'autoqcm', update=False)
    compiler.add_new_tag('GRAY_IF_CORRECT', (2, 0, None), AutoQCMTags._parse_GRAY_IF_CORRECT_tag, 'autoqcm', update=False)
    compiler.add_new_tag('DEBUG_AUTOQCM', (0, 0, None), AutoQCMTags._parse_DEBUG_AUTOQCM_tag, 'autoqcm', update=True)
    code, students_list, n_questions, n_max_answers = generate_tex(text)
    compiler.latex_generator.autoqcm_data = {'answers': {},
            'students': students_list, 'n_questions': n_questions,
            'n_max_answers': n_max_answers,
            'correct': 1,
            'incorrect': -1/n_max_answers,
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


