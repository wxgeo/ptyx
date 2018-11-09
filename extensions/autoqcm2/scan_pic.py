from math import degrees, atan, hypot
import builtins
from functools import partial

from PIL import Image
from numpy import array, flipud, fliplr, dot


from square_detection import test_square_color, find_black_square, \
                             eval_square_color,  \
                             find_lonely_square, color2debug
from config_parser import load
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
CORNER_NAMES = {'tl': 'top-left', 'tr': 'top-right', 'bl': 'bottom-left',
                'br': 'bottom-right'}

#TODO: calibrate grayscale too.
#At the bottom of the page, display 5 squares:
# Black - Gray - Light gray - White - Light gray - Gray - Black


def round(f, n=None):
    # PEP3141 compatible round() implementation.
    # round(f) should return an integer, but the problem is
    # __builtin__.round(f) doesn't return an int if type(f) is np.float64.
    # See: https://github.com/numpy/numpy/issues/11810
    return (int(builtins.round(f)) if n is None else builtins.round(f, n))


def transform(pic, transformation, *args, **kw):
    "Return a transformed version of `pic` and its matrix."
    # cf. http://stackoverflow.com/questions/5252170/specify-image-filling-color-when-rotating-in-python-with-pil-and-setting-expand
    rgba = pic.convert('RGBA')
    rgba = getattr(rgba, transformation)(*args, **kw)
    white = Image.new('RGBA', rgba.size, (255, 255, 255, 255))
    out = Image.composite(rgba, white, rgba)
    pic = out.convert(pic.mode)
    return pic, array(pic)/255.



def find_corner_square(m, size, corner, tolerance, whiteness):
    L, l = m.shape
    V, H = corner
    if V == 'b':
        m = flipud(m)
    if H == 'r':
        m = fliplr(m)
    area = m[:L//4,:l//4]
    positions = find_lonely_square(area, size, error=tolerance, gray_level=whiteness)
    def norm(ij):
        return l*ij[0] + L*ij[1]
    try:
        i, j = min(positions, key=norm)
    except ValueError:
        raise LookupError(f"No lonely black square in {CORNER_NAMES[corner]} corner !")
    if V == 'b':
        i = L - 1 - i - size
    if H == 'r':
        j = l - 1 - j - size
    return i, j, norm((i, j))


def orthogonal(corner, positions):
    V, H = corner
    corner1 = V + ('l' if H == 'r' else 'r')
    corner2 = ('t' if V == 'b' else 'b') + H
    i, j = positions[corner]
    i1, j1 = positions[corner1]
    i2, j2 = positions[corner2]
    v1 = i1 - i, j1 - j
    v2 = i2 - i, j2 - j
    cos_a = dot(v1, v2)/(hypot(*v1)*hypot(*v2))
    return abs(cos_a) < 0.06


def area_opposite_corners(positions):
    i1 = round((positions['tl'][0] + positions['tr'][0])/2)
    i2 = round((positions['bl'][0] + positions['br'][0])/2)
    j1 = round((positions['tl'][1] + positions['bl'][1])/2)
    j2 = round((positions['tr'][1] + positions['br'][1])/2)
    return (i1, j1), (i2, j2)


def detect_four_squares(m, square_size, cm, max_alignment_error_cm=.4, debug=False):
    h = w = round(2*(1 + SQUARE_SIZE_IN_CM)*cm)
    tolerance = 0.4
    whiteness = 0.45
    # Make a mutable copy of frozenset CORNERS.
    corners = set(CORNERS)
    positions = {}
    give_up = False
    while len(positions) < 4 and not give_up:
        for corner in CORNERS:
            try:
                i, j, norm = find_corner_square(m, square_size, corner, tolerance, whiteness)
                # ~ # We may have only detected a part of the square by restricting
                # ~ # the search area, so extend search by the size of the square.
                # ~ i, j = find_corner_square(m, square_size, corner, h + square_size,
                                          # ~ w + square_size, tolerance, whiteness)
                color2debug(m, (i, j), (i + square_size, j + square_size), display=False)
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
        # ~ if input(len(positions)) == 'd':
            # ~ color2debug(m)

    # If one calibration square is missing (a corner of the sheet is
    # folded for example), it will be generated from the others.

    if len(positions) <= 2:
        color2debug(m)
        raise RuntimeError('Only 2 squares found, calibration failed !')

    # If there are 4 squares, and one is less dark than the others,
    # let's drop it and use only the 3 darkers.
    # (The 4th square will be generated again using the position of the 3 others).

    for V in 'tb':
        if positions[f'{V}r'][0] - positions[f'{V}l'][0] > max_alignment_error_cm*cm:
            print("Warning: Horizontal alignment problem in corners squares !")
            debug = True
    for H in 'lr':
        if positions[f'b{H}'][1] - positions[f't{H}'][1] > max_alignment_error_cm*cm:
            print("Warning: Vertical alignment problem in corners squares !")
            debug = True

    # Try to detect false positives.
    if len(positions) == 4:
        # If only one corner is orthogonal, the opposite corner must be wrong.
        n = 0
        for corner in positions:
            if orthogonal(corner, positions):
                n += 1
                orthogonal_corner = corner
        if n == 1:
            V, H = orthogonal_corner
            opposite_corner = ('t' if V == 'b' else 'b') + ('l' if H == 'r' else 'r')
            print(f'Removing {CORNER_NAMES[opposite_corner]} corner (not orthogonal !)')
            del positions[opposite_corner]


    if len(positions) == 4:
        darkness = {}
        for corner, position in positions.items():
            darkness[corner] = eval_square_color(m, *position, square_size)

        lighter_corner = min(darkness, key=darkness.get)
        if darkness[lighter_corner] < 0.4:
            print(f'Removing {CORNER_NAMES[lighter_corner]} corner (too light !)')
            del positions[lighter_corner]

    if len(positions) == 4:
        if n <= 2:
            color2debug(m)
            print('n =', n)
            raise RuntimeError("Something wrong with the corners !")


    for corner in CORNERS:
        if corner not in positions:
            print(f'Warning: {CORNER_NAMES[corner]} corner not found.\n'
                   'Its position will be deduced from the 3 other corners.')
            V, H = corner # 'b' 'r'
            nV, nH = ('t' if V == 'b' else 'b'), ('l' if H == 'r' else 'r')
            # This is the opposite corner of the missing one.
            i0, j0 = positions[nV + nH]
            i1, j1 = positions[nV + H]
            i2, j2 = positions[V + nH]
            i = i2 + (i1 - i0)
            j = j2 + (j1 - j0)

            # Calculate the last corner (ABCD parallelogram <=> Vec{AB} = \Vec{DC})
            positions[corner] = (i, j)
            color2debug(m, (i, j), (i + square_size, j + square_size), color="cyan", display=False)

            # For example: positions['bl'] = positions['br'][0], positions['tl'][1]


    ij1, ij2 = area_opposite_corners(positions)

    if debug:
        color2debug(m, ij1, ij2, color='green')
    else:
        color2debug()

    return positions, ij1, ij2



def find_ID_band(m, i, j1, j2, square_size):
    "Return the top left corner (coordinates in pixels) of the ID band first square."
    margin = square_size
    i1, i2 = i - margin, i + square_size + margin
    j1, j2 = j1 + 3*square_size, j2 - 2*square_size
    color2debug(m, (i1, j1), (i2, j2), display=False)
    search_area = m[i1:i2, j1:j2]
    i3, j3 = find_black_square(search_area, size=square_size,
                            error=0.3, mode='c', debug=False).__next__()
    return i1 + i3, j1 + j3



def calibrate(pic, m, debug=False):
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
    print(f"Detect pixels/cm: {cm} (dpi: {2.54*cm})")

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

    # First pass, to detect rotation.
    positions, *_ = detect_four_squares(m, square_size, cm, max_alignment_error_cm=2, debug=debug)
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
    rotation_v = degrees(.5*(rotation_v1 + rotation_v2))
    print("Detected rotation (v): %s degrees." % round(rotation_v, 4))

    # Rotate page.
    # (rotation_v should be a bit more precise than rotation_h).
    rotation = (rotation_h + 1.5*rotation_v)/2.5
    print(f'Rotate picture: {round(rotation, 4)}°')
    pic, m = transform(pic, 'rotate', rotation, resample=Image.BICUBIC, expand=True)

    (i1, j1), (i2, j2) = positions['tl'], positions['br']
    # Distance between the (top left corners of the) left and right squares is:
    # 21 cm - 2 cm (margin left and margin right) - SQUARE_SIZE_IN_CM (1 square)
    h_pixels_per_mm = (j2 - j1)/(190 - 10*SQUARE_SIZE_IN_CM)
    # Distance between the (top left corners of the) top and bottom squares is:
    # 29.7 cm - 2 cm (margin left and margin right) - SQUARE_SIZE_IN_CM (1 square)
    v_pixels_per_mm = (i2 - i1)/(277 - 10*SQUARE_SIZE_IN_CM)
    cm = 10*(h_pixels_per_mm + 1.5*v_pixels_per_mm)/2.5
    print(f"Detect pixels/cm: {cm}")

    # Redetect calibration squares.
    positions, (i1, j1), (i2, j2) = detect_four_squares(m, square_size, cm, debug=debug)


    try:
        i3, j3 = find_ID_band(m, i1, j1, j2, square_size)
    except StopIteration:
        # Orientation probably incorrect.
        print('Reversed page detected: 180° rotation.')
        pic, m = transform(pic, 'transpose', method=Image.ROTATE_180)
        L, l = m.shape
        p = positions
        for corner in p:
            i, j = p[corner]
            i = L - 1 - i - square_size
            j = l - 1 - j - square_size
            V, H = corner
            p[corner] = i, j
            color2debug(m, (i, j), (i + square_size, j + square_size), display=False)
        # Replace each tag by the opposite (top-left -> bottom-right).
        p['tl'], p['bl'], p['br'], p['tr'] = p['br'], p['tr'], p['tl'], p['bl']
        # ~ color2debug(m)
        (i1, j1), (i2, j2) = area_opposite_corners(positions)
        # Redetect calibration squares.
        # ~ positions, (i1, j1), (i2, j2) = detect_four_squares(m, square_size, cm, debug=debug)
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
    cm = (h_pixels_per_mm + 1.5*v_pixels_per_mm)/2.5


    print(positions)
    for c, (i, j) in positions.items():
        color2debug(m, (i, j), (i + square_size, j + square_size), display=False)
    color2debug(m, (i3, j3), (i3 + square_size, j3 + square_size), display=False)
    if debug:
        color2debug(m)
    else:
        color2debug()
    # ~ input('- pause -')

    return m, h_pixels_per_mm, v_pixels_per_mm, positions['tl'], (i3, j3)



def scan_picture(filename, config, manual_verification=None, debug=False):
    """Scan picture and return page identifier and list of answers for each question.

    - `filename` is a path pointing to a PNG file.
    - `config` is either a path poiting to a config file, or a dictionnary
      containing the configuration (generated from a config file).
    - `manual_verification` is set to `True`, the picture will be displayed
      with the interpretation done by this algorithm: checkboxes considered
      blackened by student will be shown in cyan, and all the other ones will be
      shown in red. If it is set to `None` (default), the user will be asked
      for manual verification only if recommanded. If it is set to `False`,
      user will never be bothered.

    Return the following dictionnary:
    {'ID': int, 'page': int, 'name': str, 'answered': dict, 'matrix': array}
      * `ID`: identifier of the test
      * `page`: page of the test
      * `name`: student name
      * `answered`: the answer selected by the student for each question
        of the test. Format: {question_number: {set of answers numbers}}
      * `matrix`: an array representing the current picture.
    """

    # Convert to grayscale picture.
    pic = Image.open(filename).convert('L')
    m = array(pic)/255.

    # ------------------------------------------------------------------
    #                          CONFIGURATION
    # ------------------------------------------------------------------
    # Load configuration.
    if isinstance(config, str):
        config = load(config)
    # ~ n_questions = config['questions']
    # ~ n_answers = config['answers (max)']
    students = config['students']
    n_students = len(students)
    ids = config['ids']


    # ------------------------------------------------------------------
    #                          CALIBRATION
    # ------------------------------------------------------------------

    m, h_pixels_per_mm, v_pixels_per_mm, (TOP, LEFT), (i, j) = calibrate(pic, m, debug=debug)
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

    # ~ color2debug(m)
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
    student_ID = ''

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

            i0, j0 = xy2ij(*config['id-table-pos'])

            #~ color2debug(m, (imin + i0, j0), (imin + i0 + height, j0 + cell_size), color=(0,255,0))
            # ~ color2debug(m, (i0, j0), (i0 + cell_size, j0 + cell_size), color=(0,255,0))

            # Scan grid row by row. For each row, the darker cell is retrieved,
            # and the associated caracter is appended to the ID.
            all_ID_are_of_the_same_length = (len(set(len(ID) for ID in ids)) == 1)

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
                digits_for_nth_caracter = sorted(digits[n])
                if all_ID_are_of_the_same_length and len(digits_for_nth_caracter) == 1:
                    # No need to read, there is no choice for this caracter !
                    student_ID += digits_for_nth_caracter.pop()
                    continue
                for k, d in enumerate(digits_for_nth_caracter):
                    # Left ot the cell.
                    j = round(j0 + (k + 1)*f_cell_size)
                    # ~ val = eval_square_color(m, i, j, cell_size)
                    # ~ print(d, val)

                    # ~ color2debug(m, (i + 2, j + 2), (i - 2 + cell_size, j - 2+ cell_size), color=(1,1,0))
                    if test_square_color(m, i, j, cell_size, gray_level=.8):
                        blackness = eval_square_color(m, i, j, cell_size)
                        black_cells.append((blackness, d))
                        print('Found:', d, blackness)
                        # ~ color2debug(m, (imin + i, j), (imin + i + cell_size, j + cell_size))
                        color2debug(m, (i, j), (i + cell_size, j + cell_size), color='cyan', display=False)
                    else:
                        color2debug(m, (i, j), (i + cell_size, j + cell_size), display=False)
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
                # ~ color2debug(m)


        else:
            print("No students list.")

        print("Student name:", student_name)




    # ------------------------------------------------------------------
    #                      READ ANSWERS
    # ------------------------------------------------------------------

    try:
        boxes = config['boxes'][identifier][page]
    except KeyError:
        raise KeyError(f'ID {identifier!r} - page {page!r} not found in config file !')

    ordering = config['ordering'][identifier]
    mode = config['mode']
    correct_answers = config['correct_answers']

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

    answered = {}
    # Store blackness of checkboxes, to help detect false positives
    # and false negatives.
    blackness = {}
    positions = {}
    for key, pos in boxes.items():
        # ~ should_have_answered = set() # for debuging only.
        i, j = xy2ij(*pos)
        q, a = key[1:].split('-')
        # Now, we have to take care of the shuffling, to find the number
        # of the correct answers.
        q = q0 = int(q)
        #XXX: answers should start at 1, not 0 (like questions) for coherence.
        a = a0 = int(a) + 1
        # `q0` and `a0` keep track of apparent question and answers numbers,
        # which will be used on output to make debuging easier.
        # Find "real" question number, ie. question number before shuffling.
        q = ordering['questions'][q - 1]
        # Find "real" answer number, ie. question number before shuffling.
        a = ordering['answers'][q][a - 1]

        answer_is_correct = (a in correct_answers)
        # ~ if answer_is_correct:
            # ~ should_have_answered.add(a0)

        test_square = partial(test_square_color, m, i + 3, j + 3, cell_size - 7)
        color_square = partial(color2debug, m, (i, j),
                               (i + cell_size, j + cell_size), display=False)

        if q not in answered:
            answered[q] = set()
            print(f'\n{ANSI_CYAN}• Question {q0}{ANSI_RESET}')

        # The following will be used to detect false positives or false negatives later.
        blackness[(q, a)] = eval_square_color(m, i + 3, j + 3, cell_size - 7)
        positions[(q, a)] = (i, j)

        if (test_square(proportion=0.2, gray_level=0.65) or
                # ~ test_square_color(m, i + 3, j + 3, cell_size - 7, proportion=0.4, gray_level=0.75) or
                # ~ test_square_color(m, i + 3, j + 3, cell_size - 7, proportion=0.45, gray_level=0.8) or
                test_square(proportion=0.4, gray_level=0.90) or
                test_square(proportion=0.6, gray_level=0.95)):
            # The student has checked this box.
            c = '■'
            is_ok = (a in correct_answers[q])
            answered[q].add(a)

            if not test_square(proportion=0.4, gray_level=0.9):
                manual_verification = (manual_verification is not False)
                color_square(color='green', thickness=5)
            else:
                color_square(color='blue', thickness=5)
        else:
            # This box was left unchecked.
            c = '□'
            is_ok = (a not in correct_answers[q])
            if test_square(proportion=0.2, gray_level=0.95):
                manual_verification = (manual_verification is not False)
                color_square(thickness=2, color='magenta')
            else:
                color_square(thickness=2)

        print(f"  {'' if is_ok else ANSI_YELLOW}{c} {a}  {ANSI_RESET}", end='\t')
        # ~ print('\nCorrect answers:', should_have_answered)
    print()

    # Test now for false negatives and false positives.

    # First, try to detect false negatives.
    # If a checkbox considered unchecked is notably darker than the others,
    # it is probably checked after all (and if not, it will most probably be catched
    # with false positives in next section).
    # Add 0.03 to 1.5*mean, in case mean is almost 0.
    ceil = 1.5*sum(blackness.values())/len(blackness) + 0.03
    for (q, a) in blackness:
        if a not in answered[q] and blackness[(q, a)] > ceil:
            print('False negative detected', (q, a))
            # This is probably a false negative, but we'd better verify manually.
            manual_verification = (manual_verification is not False)
            answered[q].add(a)
            # Change box color for manual verification.
            i, j = positions[(q, a)]
            color2debug(m, (i, j), (i + cell_size, j + cell_size), color='green', thickness=5, display=False)

    # If a checkbox is tested as checked, but is much lighter than the darker one,
    # it is very probably a false positive.
    floor = max(.2*max(blackness.values()), max(blackness.values()) - 0.3)
    for (q, a) in blackness:
        if a in answered[q] and blackness[(q, a)] < floor:
            print('False positive detected', (q, a))
            # This is probably a false positive, but we'd better verify manually.
            manual_verification = (manual_verification is not False)
            answered[q].discard(a)
            # Change box color for manual verification.
            i, j = positions[(q, a)]
            color2debug(m, (i, j), (i + cell_size, j + cell_size), color='magenta', thickness=5, display=False)


    # ~ color2debug(m, (0,0), (0,0), display=True)
    # ~ print(f'\nScore: {ANSI_REVERSE}{score:g}{ANSI_RESET}\n')
    if debug or (manual_verification is True):
        color2debug(m)
    else:
        color2debug()

    return {'ID': identifier, 'page': page, 'name': student_name, 'answered': answered, 'matrix': m}

