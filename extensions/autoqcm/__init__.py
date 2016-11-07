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


class AutoQCMTags(object):
    def _parse_NEW_QCM_tag(self, node):
        self.autoqcm_correct_answers = []

    def _parse_END_QCM_tag(self, node):
        # TODO: Store QCM with NUM value.
        n = self.context['NUM']
        self.autoqcm_data['answers'][n] = self.autoqcm_correct_answers


    def _parse_NEW_QUESTION_tag(self, node):
        self.autoqcm_correct_answers.append([])
        self.autoqcm_answer_number = 0

    def _parse_NEW_ANSWER_tag(self, node):
        self.autoqcm_answer_number += 1
        if (node.arg(0) == 'True'):
            self.autoqcm_correct_answers[-1].append(self.autoqcm_answer_number)

    def _parse_AUTOQCM_HEADER_tag(self, node):
        n = self.context['NUM']
        self.write(generate_identification_band(identifier=n))

    def _parse_DEBUG_AUTOQCM_tag(self, node):
        ans = self.autoqcm_correct_answers
        print('---------------------------------------------------------------')
        print('AutoQCM answers:')
        print(ans)
        print('---------------------------------------------------------------')
        self.write(ans)

def main(text, compiler):
    # For efficiency, update only for last tag.
    compiler.add_new_tag('NEW_QCM', (0, 0, None), AutoQCMTags._parse_NEW_QCM_tag, 'autoqcm', update=False)
    compiler.add_new_tag('NEW_QUESTION', (0, 0, None), AutoQCMTags._parse_NEW_QUESTION_tag, 'autoqcm', update=False)
    compiler.add_new_tag('NEW_ANSWER', (1, 0, None), AutoQCMTags._parse_NEW_ANSWER_tag, 'autoqcm', update=False)
    compiler.add_new_tag('END_QCM', (0, 0, None), AutoQCMTags._parse_END_QCM_tag, 'autoqcm', update=False)
    compiler.add_new_tag('AUTOQCM_HEADER', (0, 0, None), AutoQCMTags._parse_AUTOQCM_HEADER_tag, 'autoqcm', update=False)
    compiler.add_new_tag('DEBUG_AUTOQCM', (0, 0, None), AutoQCMTags._parse_DEBUG_AUTOQCM_tag, 'autoqcm', update=True)
    code, students_list, n_questions, n_max_answers = generate_tex(text)
    compiler.latex_generator.autoqcm_data = {'answers': {},
            'students': students_list, 'n_questions': n_questions,
            'n_max_answers': n_max_answers,}
    assert isinstance(code, str)
    return code

def close(compiler):
    g = compiler.latex_generator
    answers = sorted(g.autoqcm_data['answers'].items())
    l = []
    l.append('QUESTIONS: %s' % g.autoqcm_data['n_questions'])
    l.append('ANSWERS (MAX): %s' % g.autoqcm_data['n_max_answers'])
    for n, correct_answers in answers:
        l.append('*** ANSWERS (TEST %s) ***' % n)
        for i, nums in enumerate(correct_answers):
            # Format: question -> correct answers
            # For example: 1 -> 1,3,4
            l.append('%s -> %s' % (i + 1, ','.join(str(j) for j in nums)))

    l.append('*** STUDENTS LIST ***')
    for name in g.autoqcm_data['students']:
        l.append(name)

    with open(compiler.path + '.autoqcm.config', 'w') as f:
        f.write('\n'.join(l))


