#import sys
#from os.path import join as abspath, dirname

#script_path = dirname(abspath(sys._getframe().f_code.co_filename))
#sys.path.insert(0, script_path)



def generate_ptyx_code(text):
    "This function translates MCQ syntax into proper pTyX code."

    #TODO: improve ability to customize this part ?

    code = []

    level_names = ('ROOT', 'QCM', 'SECTION', 'QUESTION',
              'VERSION', 'ANSWERS_BLOCK', 'NEW_ANSWER')
    levels = dict(enumerate(level_names))
    depth = {name: i for i, name in enumerate(level_names)}
#    stack = StaticStack(levels)
    current_level = levels[0]

    def next_level(level):
        return levels[depth[level] + 1]
    def previous_level(level):
        return levels[depth[level] - 1]

    def begin(level, **kw):
        nonlocal current_level

        if level not in level_names:
            raise RuntimeError(f'Unknown level: {level}')

        # Current level must be the parent one before opening level.
        target = depth[level] - 1
        while depth[current_level] > target:
            close(current_level)
        while depth[current_level] < target:
            begin(next_level(current_level))
        assert depth[current_level] == target

        current_level = level
        l = []
        if level == 'QUESTION':
            l.append('#CONSECUTIVE_QUESTION' if kw.get('consecutive')
                                                else '#NEW_QUESTION')
        else:
            l.append(f'#{level}')

        if level == 'QCM':
            if kw.get('shuffle', True):
                # Shuffle sections.
                l.append('[shuffle]')
        elif level == 'SECTION':
            if 'title' in kw:
                l.append('[%s]' % kw['title'])
        elif level in ('NEW_ANSWER', 'VERSION'):
            l.append('{%s}' % kw['n'])

        code.append(''.join(l))


    def close(level):
        """Close `level` (and any opened upper one).

        For example, close('SECTION') will close levels until returning
        to a level lower than SECTION ('ROOT' or 'QCM').
        Any opened upper level ('QUESTION_BLOCK' or 'ANSWERS') will be closed first.
        """
        nonlocal current_level

        if depth[current_level] < depth[level]:
            raise RuntimeError(f"I can not close level {level}, since it is not opened !")
        while depth[current_level] > depth[level]:
            close(current_level)

        current_level = previous_level(level)
        if level == 'QCM':
            code.append('#END_QCM')

        elif level == 'ANSWERS_BLOCK':
            # If there are any blank lines after an answer, they must appear
            # *after* #END_ANSWERS_BLOCK, so move them.
            i = 0
            while code[-1].strip() == '':
                code.pop()
                i += 1
            code.append('#END_ANSWERS_BLOCK')
            code.extend(i*[''])
            # Note that since a single blank line is used to separate answers
            # blocks, user must use two consecutive blanks lines to generate
            # a new LaTeX paragraph (the first one is automatically stripped).
            #XXX: This must appear in doc.


    previous_line = None
    before_QCM = True
    is_header = False
    header = ['#QCM_HEADER{']
    question_num = 0
    correct_answers = {}

    # Don't use ASK_ONLY: if one insert Python code here, it would be removed
    # silently when generating the pdf files with the answers !
    intro = ['#ASK % (introduction)']

    for _line_ in text.split('\n'):
        line = _line_.strip()
        n = len(line)

        if n >= 3 and all(c == '<' for c in line):  # <<<
            # start MCQ
            header.append('}')
            code.extend(header)

            intro.append('#END % (introduction)')
            code.extend(intro)
            print('Parsing QCM...\n')
            print('STRUCTURE:\n')
            begin('QCM')
            before_QCM = False

        elif before_QCM:
            if n >= 3 and all(c == '=' for c in line):  # ===
                # Enter (or leave) header section.
                is_header = not is_header
            elif is_header:
                header.append(_line_)
            else:
                intro.append(_line_)

        elif n >= 3 and line.startswith('=') and line.endswith('='):
            # === title ===
            # Start a new section.
            begin('SECTION', title=line.strip('= '))

        # Nota: for a new version of a question, line must start with 'OR ',
        # with a trailing space, or line must be 'OR', without trailing space.
        elif any(line.startswith(s) for s in ('* ', '> ', 'OR ')) or line == 'OR':
            # * question
            # Start a question block, with possibly several versions of a question.

            if line[:2] != 'OR':
                # If line starts with 'OR', this is not a new block, only another
                # version of current question block.
                # In all other cases, this is a new question.

                begin('QUESTION', consecutive=(line[0]=='>'))
            question_num += 1
            begin('VERSION', n=question_num)
            correct_answers[question_num] = []
            answer_num = 0
            code.append(line[2:])

        elif line.startswith('#L_ANSWERS'):
            # End question.
            # (Usually, questions are closed when seeing answers, ie. lines
            # introduced by '-' or '+').
            code.append(line)
            # Correct answer will always be first one.
            # (This is simpler to deal with, since list size may vary.)
            correct_answers[question_num].append(1)

        elif line.startswith('@'):
            raw = line.startswith('@@')
            formatting = line[(2 if raw else 1):].strip()
            if formatting == '':
                formatting = '%s'
            # Declare function to be applied to all answers.
            code.append(f'#{{RAW_CODE={raw};APPLY_TO_ANSWERS={formatting!r};}}')

        elif line.startswith('- ') or line.startswith('+ '):
            # - incorrect answer
            # + correct answer

            # A blank line is used to separate answers groups.
            if previous_line == '' and current_level == 'NEW_ANSWER':
                # This blank line should not appear in final pdf, so remove it.
                # (NB: This must *not* be done for the first answer !)
                code.pop()

            if previous_line == '' or previous_line.startswith('@'):
                # Answers are shuffled inside their respective groups,
                # however groups are kept separate.
                if previous_line.startswith('@'):
                    cut_and_paste = code.pop()
                begin('ANSWERS_BLOCK')
                if previous_line.startswith('@'):
                    code.append(cut_and_paste)



            answer_num += 1
            begin('NEW_ANSWER', n=answer_num)

            if line[0] == '+':
                # This is a correct answer.
                correct_answers[question_num].append(answer_num)

            code.append(line[2:])

#        elif n >= 3 and all(c == '-' for c in line):  # ---
#            if stack.current == 'ANSWERS':
#                close('ANSWERS')

        elif n >= 3 and all(c == '>' for c in line):  # >>>
            # End MCQ
            close('QCM')

        else:
            code.append(_line_)

        previous_line = line

    code.append(r'\cleardoublepage')
    code.append(r'\end{document}')
    return '\n'.join(code), correct_answers
