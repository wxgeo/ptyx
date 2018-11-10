import sys
from os.path import join as abspath, dirname

script_path = dirname(abspath(sys._getframe().f_code.co_filename))
sys.path.insert(0, script_path)




class StaticStack():
    """This is a fixed values "stack".

    This "stack" is initialized with a tuple of successive values.
    Thoses values are accessible through `.level` attribute.

    One can only go up or down in the stack ; stack `.state` consist of all
    values below current position (values above are supposed not in the stack).
    We start at position 0.

    We can't go below first level, nor above last level.

    As a consequence, this "stack" can never be empty.

    >>> s = StaticStack(('a', 'b', 'c'))
    >>> s.levels
    ('a', 'b', 'c')
    >>> s.state
    ('a',)
    >>> s.up() # Return last top value.
    'a'
    >>> s.state
    ('a', 'b')
    >>> s.up()
    'b'
    >>> s.state
    ('a', 'b', 'c')
    >>> s.current
    'c'
    >>> s.up()
    IndexError: Can't go higher than c !
    >>> s.down()
    'c'
    >>> s.current
    'b'
    >>> 'c' in s
    False
    >>> s[-1]
    'b'
    >>> len(s)
    2
    >>> s.pos    # s[s.pos] == s[-1] == s.current is always True
    1
    >>> print(s)
    a, b (c)
    """

    def __init__(self, levels:tuple):
        self.__levels = levels
        self.__i = 0

    @property
    def levels(self):
        return self.__levels

    def up(self):
        "Go up in the stack and return previous level."
        if self.__i == len(self.__levels) - 1:
            raise IndexError("Can't go higher than %s !" % self.__levels[-1])
        self.__i += 1
        return self.__levels[self.__i - 1]

    def down(self):
        "Go down in the stack and return previous level."
        if self.__i == 0:
            raise IndexError("Can't go lower than %s !" % self.__levels[0])
        self.__i -= 1
        return self.__levels[self.__i + 1]

    @property
    def state(self):
        return self.__levels[:self.__i + 1]

    def __contains__(self, value):
        return value in self.state

    @property
    def pos(self):
        return self.__i

    def __len__(self):
        return self.__i + 1

    @property
    def current(self):
        return self.__levels[self.__i]

    def __getitem__(self, i):
        return self.state[i]

    def __str__(self):
        return ', '.join(str(v) for v in self.state) + \
                ' (%s)' % ', '.join(str(v) for v in self.levels[self.__i + 1:])











def generate_ptyx_code(text):

    #TODO: improve ability to customize this part ?

    code = []

    levels = ('ROOT', 'QCM', 'SECTION', 'QUESTION_BLOCK', 'ANSWERS')
    stack = StaticStack(levels)


    def begin(level, **kw):

        # Keep track of previous level: this is useful to know if a question block
        # is the first of a section, for example.
        previous_level = stack.current
        # First, close any opened level until founding a parent.
        close(level)

        if level == 'QCM':
            code.append('#QCM')
            code.append('#SHUFFLE % (sections)')

        elif level == 'SECTION':
            code.append('#ITEM % shuffle sections')
            if 'title' in kw:
                code.append(r'\section{%s}' % kw['title'])

        elif level == 'QUESTION_BLOCK':
            if stack.current == 'QCM':
                begin('SECTION')

            if previous_level in ('SECTION', 'QCM'):
                # This is the first question block.
                # NB: \begin{enumerate} must not be written just after the begining
                # of the section, since there may be some explanations between
                # the section title and the first question.
                code.append('\\begin{enumerate}[resume]')
                code.append('#SHUFFLE % (questions)')
            #~ # Open a section to add a \\begin{enumerate} only once.
            #~ if stack[-1] != 'SECTION':
                #~ begin('SECTION')
            # Question blocks are shuffled. As an exception, a block starting
            # with '>' must not be separated from previous block.
            if kw.get('shuffle', True):
                code.append('#ITEM % shuffle questions') # shuffle blocks.
            code.append('\\pagebreak[3]\\item')
            code.append('\\setcounter{answerNumber}{0}')
            code.append('#PICK % (question)')

        elif level == 'ANSWERS':
            # First, end question.
            code.append('#END % question\n\\nopagebreak[4]')
            # Shuffle answers.
            code.append('#ANSWERS_BLOCK')
            code.append('#SHUFFLE % (answers)')

        else:
            raise RuntimeError('Unknown level: %s' % level)

        #~ elif tag == 'NEW_QUESTION':
            #~ stack.append(
            #~ code.append('#NEW_QUESTION')
            #~ answer_number = 0

        print(stack.pos*4*' ' + 'begin %s' % level)
        stack.up()
        assert stack.current == level

        #~ if tag == 'QUESTION_BLOCK':
            #~ begin('NEW_QUESTION')


    def close(level):
        """Close `level` (and any opened upper one).

        For example, close('SECTION') will close levels until returning
        to a level lower than SECTION ('ROOT' or 'QCM').
        Any opened upper level ('QUESTION_BLOCK' or 'ANSWERS') will be closed first.
        """

        while level in stack:
            # Note that close('ROOT') will raise an error, as expected.
            _level = stack.down()
            print(stack.pos*4*' ' + 'close %s' % _level)
            #~ print('Current code: %s' % repr(code[-20:]))

            # Specify how to close each level.
            if _level == 'QCM':
                code.append('#END_SHUFFLE % (sections)')
                code.append('#END_QCM')

            elif _level == 'SECTION':
                code.append('#END_SHUFFLE % (questions)')
                code.append(r'\end{enumerate}')

            elif _level == 'QUESTION_BLOCK':
                code.append('#END_PICK % (question)')

            elif _level == 'ANSWERS':
                # Remove  blank lines which may be placed between two answers
                # when shuffling.
                while code[-1].strip() == '':
                    code.pop()
                code.append('#END_SHUFFLE % (answers)')
                code.append('#END % (answers block)')



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

        elif any(line.startswith(s) for s in ('* ', '> ', 'OR ')) or line == 'OR':
            # * question
            # Start a question block, with possibly several versions of a question.

            if line[:2] == 'OR':
                # If line starts with 'OR', this is not a new block, only another
                # version of current question block.
                close('ANSWERS')
            else:
                # This is a new question.
                begin('QUESTION_BLOCK', shuffle=(line[0]=='*'))
            code.append('#ITEM % pick a version') # pick a block.

            question_num += 1
            code.append(f'#NEW_QUESTION{{{question_num}}}')
            correct_answers[question_num] = []
            answer_num = 0
            code.append(line[2:])

        elif line.startswith('#L_ANSWERS'):
            # End question.
            # (Usually, questions are closed when seeing answers, ie. lines
            # introduced by '-' or '+').
            code.append('#END % question (before l_answers)')
            code.append(line)
            # Correct answer will always be first one.
            # (This is simpler to deal with, since list size may vary.)
            correct_answers[question_num].append(1)

        elif line.startswith('@'):
            code.append('#{APPLY_TO_ANSWERS=%s;}' % repr(line[1:]))

        elif line.startswith('- ') or line.startswith('+ '):
            # - incorrect answer
            # + correct answer

            assert stack.current in ('ANSWERS', 'QUESTION_BLOCK')

            if stack.current == 'QUESTION_BLOCK':
                # This is the first answer of a new answer block.
                begin('ANSWERS')

            elif previous_line == '':
                # A blank line may be used to separate answers groups.
                # (It should not appear in final pdf, so overwrite it).
                # (NB: This must not be done for the first answer !)
                code[-1] = '#END_SHUFFLE % (answers)'
                code.append('#SHUFFLE % (answers)')

            code.append('#ITEM % shuffling answers')
            answer_num += 1
            code.append(f'#NEW_ANSWER{{{answer_num}}}')
            if line[0] == '+':
                # This is a correct answer.
                correct_answers[question_num].append(answer_num)

            code.append('#PROPOSED_ANSWER %s#END' % line[2:])

        elif n >= 3 and all(c == '-' for c in line):  # ---
            if stack.current == 'ANSWERS':
                close('ANSWERS')

        elif n >= 3 and all(c == '>' for c in line):  # >>>
            # End MCQ
            close('QCM')

        else:
            code.append(_line_)

        previous_line = line

    code.append(r'\cleardoublepage')
    code.append(r'\end{document}')
    return '\n'.join(code), correct_answers



