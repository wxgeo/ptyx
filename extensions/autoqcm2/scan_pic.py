from math import degrees, atan

from PIL import Image
from numpy import array


from square_detection import test_square_color, find_black_square, \
                             eval_square_color, find_black_rectangle, \
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
    #~ while True:
        #~ print(eval(input('>>>'), globals(), locals()))
    #~ m = convert_png_to_gray(m)

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
    rotation_set = False
    flip_set = False
    step = 0
    while True:
        step += 1
        print(f"Calibration: step {step}")
        # Evaluate approximatively squares size using image dpi.
        # Square size is equal to SQUARE_SIZE_IN_CM in theory, but this vary
        # in practice depending on printer and scanner configuration.
        # Unit conversion: 1 inch = 2.54 cm
        dpi = 2.54*m.shape[1]/21
        print("Detect dpi: %s" % dpi)
        square_size = int(round(SQUARE_SIZE_IN_CM*dpi/2.54))
        #~ print("Square size 1st estimation (pixels): %s" % square_size)

        #~ print("Squares list:\n" + str(detect_all_squares(m, square_size, 0.5)))

        # Detecting the top 2 squares (at the top left and the top right of the
        # page) to calibrate. Since square size is not known precisely,
        # keep a high error rate for now.
        maxi = maxj = maxj0 = int(round(2*(1 + SQUARE_SIZE_IN_CM)*dpi/2.54))
        # First, search the top left black square.
        while True:
            #~ color2debug(m, (0, 0), (maxi, maxj), color=(0,255,0), display=True)
            try:
                #~ i1, j1 = find_black_square(m[:maxi,:maxj], size=square_size, error=0.5).__next__()
                i1, j1 = find_lonely_square(m[:maxi,:maxj], size=square_size, error=0.5)
                #~ color2debug(m, (i1, j1), (i1 + square_size, j1 + square_size), color=(255,255,0), display=True)
                break
            except (StopIteration, TypeError):
                # Top left square not found.
                # Expand search area, mostly vertically (expanding to much
                # horizontally may induce false positives, because of the QR code).
                print('Adjusting search area...')
                maxi += square_size
                if maxj < maxj0 + 4*square_size:
                    maxj += square_size//2

        # Search now for the top right black square.
        minj = minj0 = int(round((20 - 2*(1 + SQUARE_SIZE_IN_CM))*dpi/2.54))
        while True:
            try:
                #~ color2debug(m, (0, minj), (maxi, None), color=(0,255,0), display=True)
                i2, j2 = find_lonely_square(m[:maxi,minj:], size=square_size, error=0.5)
                j2 += minj
                break
            except (StopIteration, TypeError):
                # Top right square not found.
                # Expand search area, mostly vertically (expanding to much
                # horizontally may induce false positives, because of the QR code).
                print('Adjusting search area...')
                maxi += square_size
                if minj > minj0 - 4*square_size:
                    minj -= square_size//2

        #~ print("Top left square at (%s,%s)." % (i1, j1))
        #~ print("Top right square at (%s,%s)." % (i2, j2))

        #~ # Control top squares position:
        #~ color2debug((i1, j1), (i1 + square_size, j1 + square_size))
        #~ color2debug((i2, j2), (i2 + square_size, j2 + square_size))

        #~ # Control top squares alignement after rotation:
        #~ if i == 2:
            #~ color2debug((i1, j1), (i1, j2 + square_size))

        if not rotation_set:
            rotation_set = True
            # Detect rotation, and rotate picture if needed.
            rotation = atan((i2 - i1)/(j2 - j1))
            print("Detect rotation: %s degrees." % degrees(round(rotation, 4)))
            # cf. http://stackoverflow.com/questions/5252170/specify-image-filling-color-when-rotating-in-python-with-pil-and-setting-expand
            rgba = pic.convert('RGBA')
            rgba = rgba.rotate(degrees(rotation), resample=Image.BICUBIC, expand=True)
            white = Image.new('RGBA', rgba.size, (255, 255, 255, 255))
            out = Image.composite(rgba, white, rgba)
            pic = out.convert(pic.mode)
            m = array(pic)/255.
            continue

        # From there, we assume that the rotation is negligable.

        # We will now evaluate squares size more precisely (printers or scanner
        # margins may result in a picture a bit scaled).
        # On the top of the paper sheet, there are two squares, one at the top left
        # and the other at the top right.
        # This is the top of the sheet:
        #                               1 cm
        #                                <->
        #   ┌╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴╴┐↑
        #   |                              |↓ 1 cm
        #   |  ■                        ■  |
        #
        # Distance between the top left corners of the top left and top right squares is:
        # 21 cm - 2 cm (margin left and margin right) - SQUARE_SIZE_IN_CM (1 square)
        pixels_per_cm = (j2 - j1)/(19 - SQUARE_SIZE_IN_CM)
        # We should now have an accurate value for square size.
        f_square_size = SQUARE_SIZE_IN_CM*pixels_per_cm
        square_size = int(round(f_square_size))
        print("Square size final value (pixels): %s (%s)" % (square_size, f_square_size))


        # ------------------------------------------------------------------
        #                      READ IDENTIFIER
        # ------------------------------------------------------------------
        # Now, detect the home made "QR code".
        # This code is made of a band of 16 black or white squares
        # (the first one is always black and is only used to detect the band).
        # ■■□■□■□■■□□□■□□■ = 0b100100011010101 =  21897
        # 2**15 = 32768 different values.

        # Restrict search area to avoid detecting anything else, like students names list.
        imin = i1 - square_size//2
        imax = i1 + (3*square_size)//2
        try:
            i3, j3 = find_black_square(m[imin:imax,maxj:minj], size=square_size,
                                       error=0.3, mode='c', debug=False).__next__()
            # Orientation seems to be OK, quit calibration phase.
            break
        except StopIteration:
            if not flip_set:
                flip_set = True
                rgba = pic.convert('RGBA')
                rgba = rgba.transpose(method=Image.ROTATE_180)
                white = Image.new('RGBA', rgba.size, (255, 255, 255, 255))
                out = Image.composite(rgba, white, rgba)
                pic = out.convert(pic.mode)
                m = array(pic)/255.
                continue
            print("ERROR: Can't find identification band, displaying search area in red.")
            color2debug(m, (imin, minj), (imax, maxj))
            raise RuntimeError("Can't find identification band !")

    i3 += imin
    j3 += maxj
    #~ print("Identification band starts at (%s, %s)" % (i3, j3))
    #~ color2debug((i3, j3), (i3 + square_size, j3), color=(0,255,0), display=False)
    #~ color2debug((i3, j3), (i3, j3 + square_size), color=(0,255,0), display=False)

    # (i3, j3) is the top left corner of the ID band.

    identifier = 0
    # Test the color of the 15 following squares,
    # and interpret it as a binary number.
    j = j3
    for k in range(24):
        j = int(round(j3 + (k + 1)*f_square_size))
        #~ if k%2:
            #~ color2debug((i3, j), (i3 + square_size, j + square_size), display=False)
        #~ else:
            #~ color2debug((i3, j), (i3 + square_size, j + square_size), color=(0,0,255), display=False)
        if test_square_color(m, i3, j, square_size, proportion=0.5, gray_level=0.5):
            identifier += 2**k
            #~ print((k, (i3, j)), " -> black")
        #~ else:
            #~ print((k, (i3, j)), " -> white")
    #~ color2debug()
    # Nota: If necessary (although this is highly unlikely !), one may extend protocol
    # by adding a second band (or more !), starting with a black square.
    # This function will test if a black square is present below the first one ;
    # if so, the second band will be joined with the first
    # (allowing 2**30 = 1073741824 different values), and so on.

    page = identifier%256
    print("Page read: %s" % page)
    identifier = identifier//256
    print("Identifier read: %s" % identifier)

    # Exclude the codebar and top squares from the search area.
    # If rotation correction was well done, we should have i1 ≃ i2 ≃ i3.
    # Anyway, it's safer to take the max of them.
    vpos = max(i1, i2, i3) + 2*square_size


    # For now, we can convert LaTeX position to pixel with a good precision.
    f_cell_size = CELL_SIZE_IN_CM*pixels_per_cm
    cell_size = int(round(f_cell_size))
    yshift = i1 - pixels_per_cm
    xshift = j1 - pixels_per_cm
    TOP = i1
    LEFT = j1
    # ~ color2debug(m, (TOP, LEFT), (TOP + square_size, LEFT + square_size))

    def xy2ij(x, y):
        '''Convert (x, y) position (mm) to pixels (i,j).

        (x, y) is the position from the bottom left of the page in mm,
        as given by LaTeX.
        (i, j) is the position in pixels, where i is the line and j the
        column, starting from the top left of the image.
        '''
        pixels_per_mm = pixels_per_cm/10
        i = (287 - y)*pixels_per_mm + TOP
        j = (x - 10)*pixels_per_mm + LEFT
        return (int(round(i)), int(round(j)))

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

            student_number = None
            search_area = m[vpos:vpos + 4*square_size,:]
            i, j0 = find_black_square(search_area, size=square_size, error=0.3, mode='c').__next__()
            #~ color2debug((vpos + i, j0), (vpos + i + square_size, j0 + square_size), color=(0,255,0))
            vpos += i + square_size

            l = []
            for k in range(1, n_students + 1):
                j = int(round(j0 + 2*k*f_square_size))
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
            height = ID_length*cell_size

            i0, j0 = xy2ij(*config['ID-table-pos'])

            #~ color2debug(m, (imin + i0, j0), (imin + i0 + height, j0 + cell_size), color=(0,255,0))
            # ~ color2debug(m, (i0, j0), (i0 + cell_size, j0 + cell_size), color=(0,255,0))

            # Scan grid row by row. For each row, the darker cell is retrieved,
            # and the associated caracter is appended to the ID.
            student_ID = ''
            for n in range(ID_length):
                # Top of the row.
                i = int(round(i0 + n*f_cell_size))
                black_cells = []
                # If a cell is black enough, a couple (indice_of_blackness, digit)
                # will be appended to the list `cells`.
                # After scanning the whole row, we will assume that the blackest
                # cell of the row will be a to be the one checked by the student,
                # as long as there is enough difference between the blackest
                # and the second blackest.
                for k, d in enumerate(sorted(digits[n])):
                    # Left ot the cell.
                    j = int(round(j0 + (k + 1)*f_cell_size))
                    # ~ val = eval_square_color(m, i, j, cell_size)
                    # ~ print(d, val)
                    # ~ color2debug(m, (i, j), (i + cell_size, j + cell_size), display=False)
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
        question = int(question)
        print(f'{ANSI_CYAN}• Question {question}{ANSI_RESET}')
        proposed = set()
        correct = set(correct_answers)
        for answer, infos in answers.items():
            answer = int(answer)
            i, j = xy2ij(*infos['pos'])

            # Remove borders of the square when testing,
            # since it may induce false positives.

            # ~ color2debug(m, (i, j), (i + cell_size, j + cell_size), display=False)
            if (test_square_color(m, i + 3, j + 3, cell_size - 7, proportion=0.2, gray_level=0.65) or
                    test_square_color(m, i + 3, j + 3, cell_size - 7, proportion=0.4, gray_level=0.75)):
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

    # ~ color2debug(m, (0,0), (0,0), display=True)
    print(f'\nScore: {ANSI_REVERSE}{score:g}{ANSI_RESET}\n')

    return {'ID': identifier, 'page': page, 'name': student_name, 'score': score}

