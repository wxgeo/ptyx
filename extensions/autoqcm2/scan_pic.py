from math import degrees, atan
import builtins

from PIL import Image
from numpy import array


from square_detection import test_square_color, find_black_square, \
                             eval_square_color,  \
                             find_lonely_square, color2debug
from config_reader import read_config
from parameters import (SQUARE_SIZE_IN_CM, CELL_SIZE_IN_CM)
from header import set_up_ID_table

ANSI_RESET = "\u001B[0m";
ANSI_BLACK = "\u001B[30m";
ANSI_RED = "\u001B[31m";
ANSI_GREEN = "\u001B[32m";
ANSI_YELLOW = "\u001B[33m";
ANSI_BLUE = "\u001B[34m";
ANSI_PURPLE = "\u001B[35m";
ANSI_CYAN = "\u001B[1;36m";
ANSI_WHITE = "\u001B[37m";
ANSI_BOLD = "\u001B[1m";
ANSI_REVERSE = "\u001B[45m";

CORNERS = frozenset(('tl', 'tr', 'bl', 'br'))


def round(f, n=None):
    # PEP3141 compatible round() implementation.
    # round(f) should return an integer, but the problem is
    # __builtin__.round(f) doesn't return an int if type(f) is np.float64.
    # See: https://github.com/numpy/numpy/issues/11810
    return (int(builtins.round(f)) if n is None else round(f))


def transform(pic, transformation, *args, **kw):
    "Return a transformed version of `pic` and its matrix."
    # cf. http://stackoverflow.com/questions/5252170/specify-image-filling-color-when-rotating-in-python-with-pil-and-setting-expand
    rgba = pic.convert('RGBA')
    rgba = getattr(rgba, transformation)(*args, **kw)
    white = Image.new('RGBA', rgba.size, (255, 255, 255, 255))
    out = Image.composite(rgba, white, rgba)
    pic = out.convert(pic.mode)
    return pic, array(pic)/255.



def find_corner_square(m, size, corner, h, w, tolerance, whiteness):
    L, l = m.shape
    if corner[0] == 't':
        i0, i1 = 0, h - 1
    else:
        i0, i1 = L - h, L - 1
    if corner[1] == 'l':
        j0, j1 = 0, w - 1
    else:
        j0, j1 = l - h, l - 1
    m = m[i0:i1,j0:j1]
    i, j = find_lonely_square(m, size, error=tolerance, gray_level=whiteness)
    return i0 +i, j0 + j



def detect_four_squares(m, square_size, cm):
    h = w = round(2*(1 + SQUARE_SIZE_IN_CM)*cm)
    tolerance = 0.4
    whiteness = 0.4
    # Make a mutable copy of frozenset CORNERS.
    corners = set(CORNERS)
    positions = {}
    n = 0
    give_up = False
    while len(positions) < 4 and not give_up:
        for corner in CORNERS:
            try:
                i, j = find_corner_square(m, square_size, corner, h, w, tolerance, whiteness)
                # ~ color2debug(m, (i, j), (i + square_size, j + square_size), display=False)
                positions[corner] = i, j
                corners.remove(corner)
            except LookupError:
                pass
        give_up = True
        if tolerance < 0.8:
            tolerance += 0.02
            give_up = False
        if whiteness < 0.7:
            whiteness += 0.01
            give_up = False
        if h < 4*cm and len(positions) < 3:
            h += 4
            give_up = False
        # ~ if input(len(positions)) == 'd':
            # ~ color2debug(m)

    # If one calibration square is missing (a corner of the sheet is
    # folded for example), it will be generated from the others.

    for corner in CORNERS:
        if corner not in positions:
            tb, lr = corner
            positions[corner] = (positions[tb + ('r' if lr == 'l' else 'r')][0],
                                 positions[('t' if tb == 'b' else 'b') + lr][1])
            # For example: positions['bl'] = positions['br'][0], positions['tl'][1]
    i1 = round((positions['tl'][0] + positions['tr'][0])/2)
    i2 = round((positions['bl'][0] + positions['br'][0])/2)
    j1 = round((positions['tl'][1] + positions['bl'][1])/2)
    j2 = round((positions['tr'][1] + positions['br'][1])/2)

    return positions, (i1, j1), (i2, j2)



def find_ID_band(m, i, j1, j2, square_size):
    "Return the top left corner (coordinates in pixels) of the ID band first square."
    margin = 4
    i1, i2 = i - margin, i + square_size + margin
    j1, j2 = j1 + 3*square_size, j2 - 2*square_size
    color2debug(m, (i1, j1), (i2, j2), display=False)
    search_area = m[i1:i2, j1:j2]
    i3, j3 = find_black_square(search_area, size=square_size,
                            error=0.3, mode='c', debug=False).__next__()
    return i1 + i3, j1 + j3



def calibrate(pic, m):
    u"Detect picture resolution and ensure correct orientation."
    # Ensure that the picture orientation is portrait, not landscape.
    L, l = m.shape
    print(f'Picture dimensions : {L}px x {l}px.')

    if L < l:
        pic, m = transform(pic, 'transpose', method=Image.ROTATE_90)
        L, l = m.shape

    assert l <= L

    # Calculate resolution (DPI and DPCM).
    cm = m.shape[1]/21
    # Unit conversion: 1 inch = 2.54 cm
    print(f"Detect dpi:  {2.54*cm}")

    # Evaluate approximatively squares size using image dpi.
    # Square size is equal to SQUARE_SIZE_IN_CM in theory, but this vary
    # in practice depending on printer and scanner parameters (margins...).
    square_size = round(SQUARE_SIZE_IN_CM*cm)

    # Detect the four squares at the top left, top right, bottom left
    # and bottom right corners of the page.
    # This squares will be used to calibrate picture more precisely.

    #   1 cm                         1 cm
    #   <->                          <->
    #   ┌╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴┐↑
    #   |                              |↓ 1 cm
    #   |  ■                        ■  |
    #   ┊                              ┊
    #   ┊                              ┊
    #   ┊                              ┊
    #   ┊                              ┊
    #   ┊                              ┊
    #   ┊                              ┊
    #   ┊                              ┊
    #   ┊                              ┊
    #   ┊                              ┊
    #   ┊                              ┊
    #   ┊                              ┊
    #   ┊                              ┊
    #   ┊                              ┊
    #   |  ■                        ■  |
    #   |                              |↑
    #   └╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴┘↓ 1 cm
    #


    # Detection algorithm is quite naive:
    # We'll search for a square alternatively in the four corners,
    # extending the search area and beeing more tolerant if needed.

    positions, *_ = detect_four_squares(m, square_size, cm)
    print(positions)

    # Now, let's detect the rotation.
    (i1, j1), (i2, j2) = positions['tl'], positions['tr']
    rotation_h1 = atan((i2 - i1)/(j2 - j1))
    (i1, j1), (i2, j2) = positions['bl'], positions['br']
    rotation_h2 = atan((i2 - i1)/(j2 - j1))
    rotation_h = degrees(.5*(rotation_h1 + rotation_h2))
    print("Detected rotation (h): %s degrees." % round(rotation_h, 4))

    (i1, j1), (i2, j2) = positions['tl'], positions['bl']
    rotation_v1 = atan((j1 - j2)/(i2 - i1))
    (i1, j1), (i2, j2) = positions['tr'], positions['br']
    rotation_v2 = atan((j1 - j2)/(i2 - i1))
    rotation_v = degrees(.5*(rotation_h1 + rotation_h2))
    print("Detected rotation (v): %s degrees." % round(rotation_v, 4))

    # Rotate page.
    # (rotation_v should be a bit more precise than rotation_h).
    rotation = (rotation_h + 1.5*rotation_v)/2.5
    print(f'Rotate picture: {round(rotation, 4)}°')
    pic, m = transform(pic, 'rotate', rotation, resample=Image.BICUBIC, expand=True)

    # Redetect calibration squares.
    positions, (i1, j1), (i2, j2) = detect_four_squares(m, square_size, cm)


    try:
        i3, j3 = find_ID_band(m, i1, j1, j2, square_size)
    except StopIteration:
        # Orientation probably incorrect.
        print('Reversed page detected: 180° rotation.')
        pic, m = transform(pic, 'transpose', method=Image.ROTATE_180)
        # Redetect calibration squares.
        positions, (i1, j1), (i2, j2) = detect_four_squares(m, square_size, cm)
        try:
            i3, j3 = find_ID_band(m, i1, j1, j2, square_size)
        except StopIteration:
            print("ERROR: Can't find identification band, displaying search areas in red.")
            print(i1, j1, i2, j2)
            color2debug(m)
            raise RuntimeError("Can't find identification band !")


    # Distance between the (top left corners of the) left and right squares is:
    # 21 cm - 2 cm (margin left and margin right) - SQUARE_SIZE_IN_CM (1 square)
    h_pixels_per_mm = (j2 - j1)/(190 - 10*SQUARE_SIZE_IN_CM)
    # Distance between the (top left corners of the) top and bottom squares is:
    # 29.7 cm - 2 cm (margin left and margin right) - SQUARE_SIZE_IN_CM (1 square)
    v_pixels_per_mm = (i2 - i1)/(277 - 10*SQUARE_SIZE_IN_CM)


    print(positions)
    for c, (i, j) in positions.items():
        color2debug(m, (i, j), (i + square_size, j + square_size), display=False)
    color2debug(m, (i3, j3), (i3 + square_size, j3 + square_size), display=False)
    # ~ color2debug(m)
    # ~ input('- pause -')

    return m, h_pixels_per_mm, v_pixels_per_mm, positions['tl'], (i3, j3)



def scan_picture(filename, config):
    """Scan picture and return page identifier and list of answers for each question.

    - filename is a path pointing to a PNG file.
    - config is either a path poiting to a config file, or a dictionnary
    containing the following keys:
      * n_questions is the number of questions
      * n_answers is the number of answers per question.
      * n_students is the number of students

    Return the following tuple:
      * int identifier: identifier of the sheet
      * list answers: a list of lists of booleans
      * str student_name: the name of the student if found, or None
      * int score: the score of the student.
      * list students: list of students names (str). May be empty.
      * list ids: list of students ID (int). May be empty.
    """

    # Convert to grayscale picture.
    pic = Image.open(filename).convert('L')
    m = array(pic)/255.

    # ------------------------------------------------------------------
    #                          CONFIGURATION
    # ------------------------------------------------------------------
    # Load configuration.
    if isinstance(config, str):
        config = read_config(config)
    # ~ n_questions = config['questions']
    # ~ n_answers = config['answers (max)']
    students = config['students']
    n_students = len(students)
    ids = config['ids']


    # ------------------------------------------------------------------
    #                          CALIBRATION
    # ------------------------------------------------------------------

    m, h_pixels_per_mm, v_pixels_per_mm, (TOP, LEFT), (i, j) = calibrate(pic, m)
    pixels_per_mm = (h_pixels_per_mm + 1.5*v_pixels_per_mm)/2.5

    # We should now have an accurate value for square size.
    f_square_size = SQUARE_SIZE_IN_CM*pixels_per_mm*10
    square_size = round(f_square_size)
    print("Square size final value (pixels): %s (%s)" % (square_size, f_square_size))

    f_cell_size = CELL_SIZE_IN_CM*pixels_per_mm*10
    cell_size = round(f_cell_size)

    # Henceforth, we can convert LaTeX position to pixel with a good precision.
    def xy2ij(x, y):
        '''Convert (x, y) position (mm) to pixels (i,j).

        (x, y) is the position from the bottom left of the page in mm,
        as given by LaTeX.
        (i, j) is the position in pixels, where i is the line and j the
        column, starting from the top left of the image.
        '''
        i = (287 - y)*v_pixels_per_mm + TOP
        j = (x - 10)*h_pixels_per_mm + LEFT
        return (round(i), round(j))


    # ------------------------------------------------------------------
    #                      READ IDENTIFIER
    # ------------------------------------------------------------------
    # Now, detect the home made "QR code".
    # This code is made of a band of 16 black or white squares
    # (the first one is always black and is only used to detect the band).
    # ■■□■□■□■■□□□■□□■ = 0b100100011010101 =  21897
    # 2**15 = 32768 different values.

    identifier = 0
    # Test the color of the 15 following squares,
    # and interpret it as a binary number.

    for k in range(24):
        j_ = round(j + (k + 1)*f_square_size)
        if k%2:
            color2debug(m, (i, j_), (i + square_size, j_ + square_size), display=False)
        else:
            color2debug(m, (i, j_), (i + square_size, j_ + square_size), color=(0,0,255), display=False)
        if test_square_color(m, i, j_, square_size, proportion=0.5, gray_level=0.5):
            identifier += 2**k
            #~ print((k, (i3, j)), " -> black")
        #~ else:
            #~ print((k, (i3, j)), " -> white")

    color2debug(m)
    # Nota: If necessary (although this is highly unlikely !), one may extend protocol
    # by adding a second band (or more !), starting with a black square.
    # This function will test if a black square is present below the first one ;
    # if so, the second band will be joined with the first
    # (allowing 2**30 = 1073741824 different values), and so on.

    page = identifier%256
    print("Page read: %s" % page)
    identifier = identifier//256
    print("Identifier read: %s" % identifier)



    # ~ yshift = i1 - pixels_per_cm
    # ~ xshift = j1 - pixels_per_cm
    # ~ color2debug(m, (TOP, LEFT), (TOP + square_size, LEFT + square_size))


    # ~ i, j = xy2ij(10, 10) # Top-left corner
    # ~ color2debug(m, (i, j), (i + cell_size, j + cell_size))

    # ~ ii, jj = xy2ij(0, 0)
    # ~ for x in range(0, 200, 10):
        # ~ i, j = xy2ij(x, 287)
        # ~ color2debug(m, (i, j), (ii, j + cell_size), display=False)
    # ~ color2debug(m, (0, 0), (0, 0), display=True)

    # ------------------------------------------------------------------
    #                  IDENTIFY STUDENT (OPTIONAL)
    # ------------------------------------------------------------------

    student_name = ''

    if page == 1:
        # Read student name directly
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~

        if n_students:
            #XXX: rewrite this section.
            # Use .pos file to retrieve exact position of first square
            # (just like in next section),
            # instead of scanning a large area to detect first black square.

            # Exclude the codebar and top squares from the search area.
            # If rotation correction was well done, we should have i1 ≃ i2 ≃ i3.
            # Anyway, it's safer to take the max of them.
            vpos = TOP + 2*square_size

            student_number = None
            search_area = m[vpos:vpos + 4*square_size,:]
            i, j0 = find_black_square(search_area, size=square_size, error=0.3, mode='c').__next__()
            #~ color2debug((vpos + i, j0), (vpos + i + square_size, j0 + square_size), color=(0,255,0))
            vpos += i + square_size

            l = []
            for k in range(1, n_students + 1):
                j = round(j0 + 2*k*f_square_size)
                l.append(test_square_color(search_area, i, j, square_size))
                #~ if k > 15:
                    #~ print(l)
                    #~ color2debug((vpos + i, j), (vpos + i + square_size, j + square_size))

            n = l.count(True)
            if n == 0:
                print("Warning: no student name !")
            elif n > 1:
                print("Warning: several students names !")
                for i, b in enumerate(l):
                    if b:
                        print(' - ', students[n_students - i - 1])
            else:
                student_number = n_students - l.index(True) - 1
                student_name = students[student_number]




        # Read student id, then find name
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        #
        elif ids:
            ID_length, max_digits, digits = set_up_ID_table(ids)
            # ~ height = ID_length*cell_size

            i0, j0 = xy2ij(*config['ID-table-pos'])

            #~ color2debug(m, (imin + i0, j0), (imin + i0 + height, j0 + cell_size), color=(0,255,0))
            # ~ color2debug(m, (i0, j0), (i0 + cell_size, j0 + cell_size), color=(0,255,0))

            # Scan grid row by row. For each row, the darker cell is retrieved,
            # and the associated caracter is appended to the ID.
            student_ID = ''
            for n in range(ID_length):
                # Top of the row.
                i = round(i0 + n*f_cell_size)
                black_cells = []
                # If a cell is black enough, a couple (indice_of_blackness, digit)
                # will be appended to the list `cells`.
                # After scanning the whole row, we will assume that the blackest
                # cell of the row will be a to be the one checked by the student,
                # as long as there is enough difference between the blackest
                # and the second blackest.
                for k, d in enumerate(sorted(digits[n])):
                    # Left ot the cell.
                    j = round(j0 + (k + 1)*f_cell_size)
                    # ~ val = eval_square_color(m, i, j, cell_size)
                    # ~ print(d, val)
                    color2debug(m, (i, j), (i + cell_size, j + cell_size), display=False)
                    # ~ color2debug(m, (i + 2, j + 2), (i - 2 + cell_size, j - 2+ cell_size), color=(1,1,0))
                    if test_square_color(m, i, j, cell_size):
                        blackness = eval_square_color(m, i, j, cell_size)
                        black_cells.append((blackness, d))
                        print('Found:', d, blackness)
                        # ~ color2debug(m, (imin + i, j), (imin + i + cell_size, j + cell_size))
                if black_cells:
                    black_cells.sort(reverse=True)
                    print(black_cells)
                    # Test if there is enough difference between the blackest
                    # and the second blackest (minimal difference was set empirically).
                    if len(black_cells) == 1 or black_cells[0][0] - black_cells[1][0] > 0.2:
                        # The blackest one is choosed:
                        digit = black_cells[0][1]
                        student_ID += digit
            if student_ID in ids:
                print("Student ID:", student_ID)
                student_name = ids[student_ID]
            else:
                print("Warning: invalid student id '%s' !" % student_ID)



        else:
            print("No students list.")

        print("Student name:", student_name)




    # ------------------------------------------------------------------
    #                      READ ANSWERS
    # ------------------------------------------------------------------

    try:
        boxes = config['boxes'][identifier - 1][page]
    except KeyError:
        raise KeyError(f'ID {identifier!r} - page {page!r} not found in config file !')

    score = 0
    mode = config['mode']

    # Detect the answers.
    print('\n=== Reading answers ===')
    print(f'Mode: *{mode}* correct answers must be checked.')
    print('Rating:')
    print(f"• {config['correct']} for correctly answered question,")
    print(f"• {config['incorrect']} for wrongly answered question,")
    print(f"• {config['skipped']} for unanswered question.")
    print("Scanning...\n")

    # Using the config file to obtain correct answers list allows some easy customization
    # after the test was generated (this is useful if some tests questions were flawed).

    for ((question, answers), correct_answers) in zip(boxes.items(),
                                         config['answers'][identifier]):
        # ~ q = '-'
        # ~ while q:
            # ~ try:
                # ~ q = input('>>>')
                # ~ print(eval(q))
            # ~ except:
                # ~ pass

        question = int(question)
        print(f'{ANSI_CYAN}• Question {question}{ANSI_RESET}')
        proposed = set()
        correct = set(correct_answers)
        print('correct:', correct)
        for answer, infos in answers.items():
            answer = int(answer)
            i, j = xy2ij(*infos['pos'])

            # Remove borders of the square when testing,
            # since it may induce false positives.

            color2debug(m, (i, j), (i + cell_size, j + cell_size), display=False)
            if (test_square_color(m, i + 3, j + 3, cell_size - 7, proportion=0.2, gray_level=0.65) or
                    test_square_color(m, i + 3, j + 3, cell_size - 7, proportion=0.4, gray_level=0.75) or
                    test_square_color(m, i + 3, j + 3, cell_size - 7, proportion=0.45, gray_level=0.8) or
                    test_square_color(m, i + 3, j + 3, cell_size - 7, proportion=0.5, gray_level=0.85)):
                c = '■'
                # ~ is_ok = infos['correct']
                is_ok = (answer in correct)
                proposed.add(answer)
            else:
                c = '□'
                # ~ is_ok = not infos['correct']
                is_ok = (answer not in correct)

            print(f"  {'' if is_ok else ANSI_YELLOW}{c} {answer + 1}  {ANSI_RESET}", end='\t')

        # *** Calculate score ***
        # Nota: most of the time, there should be only one correct answer.
        # Anyway, this code intends to deal with cases where there are more
        # than one correct answer too.
        # If mode is set to 'all', student must check *all* correct propositions ;
        # if not, answer will be considered incorrect. But if mode is set to
        # 'some', then student has only to check a subset of correct propositions
        # for his answer to be considered correct.
        if mode == 'all':
            ok = (correct == proposed)
        elif mode == 'some':
            # Answer is valid if and only if :
            # (proposed ≠ ∅ and proposed ⊆ correct) or (proposed = correct = ∅)
            ok = (proposed and proposed.issubset(correct)) or (not proposed and not correct)
        else:
            raise RuntimeError('Invalid mode (%s) !' % mode)

        if ok:
            earn = config['correct']
            color = ANSI_GREEN
        elif not proposed:
            earn = config['skipped']
            color = ANSI_YELLOW
        else:
            earn = config['incorrect']
            color = ANSI_RED
        print(f'\n  {color}Rating: {color}{earn:g}{ANSI_RESET}\n')
        score += earn

    color2debug(m, (0,0), (0,0), display=True)
    print(f'\nScore: {ANSI_REVERSE}{score:g}{ANSI_RESET}\n')

    return {'ID': identifier, 'page': page, 'name': student_name, 'score': score}

