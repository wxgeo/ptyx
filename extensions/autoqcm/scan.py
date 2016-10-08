from math import atan, degrees
from numpy import array#, apply_along_axis
from pylab import imread
#~ from PIL import Image

#~ from pbm_tools import lire_image

from parameters import SQUARE_SIZE_IN_CM, CELL_SIZE_IN_CM


# Much too slow ! (~ 30s to convert a 150 dpi A4 picture)
#~ def read_black_and_white_png(name):
    #~ # Read from PNG file.
    #~ m = imread(name)
    #~ # Convert to black and white picture (True means black, False means white).
    #~ def is_black(pixel):
        #~ r, g, b, a = pixel
        #~ return min(r, g, b) < 0.5 or r + g + b < 2
    #~ return apply_along_axis(is_black, 2, m)


def read_black_and_white_png(name):
    # Read from PNG file.
    m = imread(name)
    # Convert to black and white picture (True means black, False means white).
    m = (m.sum(2) < 3.5) | (m.min(2) < 0.7)
    # Since alpha is always 1, previous code means pixel is black if and only if
    # min(r, g, b) < 0.5 or r + g + b < 2.
    return m



#~ def find_black_pixel(matrix):
    #~ """Find a black pixel starting from top left corner.

    #~ Matrix is scanned line by line.

    #~ Return a generator of (i, j) where i is line number and j is column number,
    #~ so that matrix[i,j] == 1.
    #~ """
    #~ m = array(matrix, copy=False)
    #~ for i, line in enumerate(m):
        #~ for j, val in enumerate(line):
            #~ if val == 1:
                #~ yield (i, j)

#~ def find_black_pixel2(matrix):
    #~ """Find a black pixel starting from top left corner.

    #~ Matrix is scanned line by line.

    #~ Return a generator of (i, j) where i is line number and j is column number,
    #~ so that matrix[i,j] == 1.
    #~ """
    #~ m = array(matrix, copy=False)
    #~ return zip(*m.nonzero())


def find_black_square(matrix, size=50, error=0.30):
    """Detect a black square of given size (edge in pixels) in matrix.

    The matrix should contain only 1 (black) and 0 (white).

    Optional parameters:
        - `error` is the ratio of white pixels allowed is the black square.

    Return a generator of (i, j) where i is line number and j is column number,
    indicating black squares top left corner.

    """
    m = array(matrix, copy=False)
    height, width = m.shape
    per_line = (1 - error)*size
    goal = per_line*size
    to_avoid = []
    # Find a black pixel, starting from top left corner,
    # and scanning line by line (ie. from top to bottom).
    for (i, j) in zip(*m.nonzero()):
        #print("Black pixel found at %s, %s" % (i, j))
        # Avoid to detect an already found square.
        if any((li_min <= i <= li_max and co_min <= j <= co_max)
                for (li_min, li_max, co_min, co_max) in to_avoid):
            continue
        assert m[i, j] == 1
        total = m[i:i+size, j:j+size].sum()
#        print("Detection: %s found (minimum was %s)." % (total, goal))
        if total >= goal:
            print("\nBlack square found at (%s,%s)." % (i, j))
            # Adjust detection if top left corner is a bit "damaged"
            # (ie. if some pixels are missing there), or if this pixel is
            # only an artefact before the square.
            i0 = i
            j0 = j
            # Note: limit adjustement range (in case there are two consecutive squares)
            for _i in range(50):
                horizontal = vertical = False
                # Horizontal adjustement:
                while abs(j - j0) < error*size and j + size + 1 < width and (m[i:i+size, j+size+1].sum() > per_line > m[i:i+size, j].sum()):
                    j += 1
                    print("j+=1")
                    horizontal = True
                if not horizontal:
                    while abs(j - j0) < error*size and j > 0 and m[i:i+size, j+size].sum() < per_line < m[i:i+size, j-1].sum():
                        j -= 1
                        print("j-=1")
                        horizontal = True
                # Vertical adjustement:
                while abs(i - i0) < error*size and i + size + 1 < height and m[i+size+1, j:j+size].sum() > per_line > m[i, j:j+size].sum():
                    i += 1
                    print("i+=1")
                    vertical = True
                if not vertical:
                    while abs(i - i0) < error*size and i > 0 and m[i+size, j:j+size].sum() < per_line < m[i-1, j:j+size].sum():
                        i -= 1
                        print("i-=1")
                        vertical = True
                if not (vertical or horizontal):
                    break
            else:
                print("Adjustement seems abnormally long... Skiping...")
            #
            #      Do not detect pixels there to avoid detecting
            #      the same square twice.
            #      ←—————————————————————————————————→
            #      ←——————————→  ←———————————————————→
            #      buffer zone      square itself
            #      ///////////   #####################
            #      ///////////   #####################
            #      ///////////   #####################
            #      ///////////   #####################
            #      ///////////   #####################
            #      ///////////   #####################
            #      ///////////   #####################
            #      ///////////   #####################
            #      ///////////   #####################
            #      ///////////   #####################
            #      ←——————————→  ←———————————————————→
            #      ≃ error*size          size

            # Avoid to detect an already found square.
            if any((li_min <= i <= li_max and co_min <= j <= co_max)
                    for (li_min, li_max, co_min, co_max) in to_avoid):
                continue

            to_avoid.append((i - error*size - 1, i + size - 2, j - error*size - 1, j + size - 2))
            print("Final position of this new square is (%s, %s)" % (i, j))
            print("Forbidden areas are now:")
            print(to_avoid)
            yield (i, j)





def detect_all_squares(matrix, size=50, error=0.30):
    return list(find_black_square(matrix, size=size, error=error))



def test_square_color(m, i, j, size, level=0.5):
    """Return True if square is black, False else.

    (i, j) is top left corner of the square, where i is line number
    and j is column number.
    level is the proportion of black pixels the square must have at least
    to be considered black.
    """
    return m[i:i+size, j:j+size].sum() > level*size**2


def read_config(pth):
    cfg = {}
    with open(pth) as f:
        for line in f:
            if line and not line.startswith("#"):
                key, val = line.split("=")
                cfg[key.strip()] = val.strip()
    return cfg


def scan_picture(m, config):
    """Scan picture and return page identifier and list of answers for each question.

    - m is either a numpy array or a path pointing to a PNG file.
    - config is either a path poiting to a config file, or a dictionnary
    containing the following keys:
      * n_questions is the number of questions
      * n_answers is the number of answers per question.
      * n_students is the number of students

    Return an integer and a list of lists of booleans.
    """

    # ------------------------------------------------------------------
    #                          CONFIGURATION
    # ------------------------------------------------------------------
    # Load configuration.
    if isinstance(m, str):
        m = read_black_and_white_png(m)
    if isinstance(config, str):
        config = read_config(config)
    n_questions = int(config['n_questions'])
    n_answers = int(config['n_answers'])
    n_students = int(config['n_students'])

    # ------------------------------------------------------------------
    #                          CALIBRATION
    # ------------------------------------------------------------------
    # Evaluate approximatively squares size using image dpi.
    # Square size is equal to SQUARE_SIZE_IN_CM in theory, but this vary
    # in practice depending on printer and scanner configuration.
    # Unit conversion: 1 inch = 2.54 cm
    dpi = 2.54*m.shape[1]/21
    print("Detect dpi: %s" % dpi)
    square_size = int(round(SQUARE_SIZE_IN_CM*dpi/2.54))
    print("Square size 1st value (pixels): %s" % square_size)

    print("Squares list:\n" + str(detect_all_squares(m, square_size, 0.5)))

    # Detecting the top 2 squares (at the top left and the top right of the
    # page) to calibrate. Since square size is not known precisely,
    # keep a high error rate for now.
    maxi = maxj = int(round(2*(1 + SQUARE_SIZE_IN_CM)*dpi/2.54))
    i1, j1 = find_black_square(m[:maxi,:maxj], size=square_size, error=0.5).__next__()
    minj = int(round((20 - 2*(1 + SQUARE_SIZE_IN_CM))*dpi/2.54))
    i2, j2 = find_black_square(m[:maxi,minj:], size=square_size, error=0.5).__next__()
    j2 += minj

    print("Top left square at (%s,%s)." % (i1, j1))
    print("Top right square at (%s,%s)." % (i2, j2))

    # Detect rotation, and rotate picture if needed.
    rotation = atan((i2 - i1)/(j2 - j1))
    print("Detect rotation: %s" % degrees(rotation))
    # TODO: rotate picture using ImageMagick or PIL if necessary
    # ImageMagick: convert -rotate
    # PIL: Image.Image.rotate()

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
    square_size = int(round(SQUARE_SIZE_IN_CM*pixels_per_cm))
    print("Square size final value (pixels): %s" % square_size)


    # ------------------------------------------------------------------
    #                      READ IDENTIFIER
    # ------------------------------------------------------------------
    # Now, detect the home made "QR code".
    # This code is made of a band of 16 black or white squares
    # (the first one is always black and is only used to detect the band).
    # ■■□■□■□■■□□□■□□■ = 0b100100011010101 =  21897
    # 2**15 = 32768 different values.

    i3, j3 = find_black_square(m[:maxi,maxj:minj], size=square_size, error=0.3).__next__()
    j3 += maxj
    print("Identification band starts at (%s, %s)" % (i3, j3))

    identifier = 0
    # Test the color of the 15 following squares,
    # and interpret it as a binary number.
    j = j3
    for k in range(15):
        j += square_size
        if test_square_color(m, i3, j, square_size, level=0.5):
            print((k, (i3, j), test_square_color(m, i3, j, square_size, level=0.5)))
            identifier += 2**k

    # Nota: If necessary (although this is highly unlikely !), one may extend protocol
    # by adding a second band (or more !), starting with a black square.
    # This function will test if a black square is present below the first one ;
    # if so, the second band will be joined with the first
    # (allowing 2**30 = 1073741824 different values), and so on.

    print("Identification: %s" % identifier)

    vpos = max(i1, i2, i3) + square_size

    # ------------------------------------------------------------------
    #                  READ STUDENT NAME (OPTIONAL)
    # ------------------------------------------------------------------
    student_number = None
    if n_students:
        search_area = m[vpos:,:]
        i, j = find_black_square(search_area, size=square_size, error=0.3).__next__()

        l = []
        for k in range(n_students):
            j += 2*square_size
            l.append(test_square_color(search_area, i, j, square_size, level=0.5))

        n = l.count(True)
        if n == 0:
            print("Warning: no student name !")
        elif n > 1:
            print("Warning: several students names !")
        else:
            student_number = n_students - l.index(True)
            print("Student number: %s" % student_number)

    vpos += i + square_size

    # ------------------------------------------------------------------
    #                      READ ANSWERS
    # ------------------------------------------------------------------
    # Detect the answers.
    # First, it's better to exclude the header of the search area.
    # If rotation correction was well done, we should have i1 ≃ i2 ≃ i3.
    # Anyway, it's safer to take the max of them.
    cell_size = int(round(CELL_SIZE_IN_CM*pixels_per_cm))
    search_area = m[vpos:,:]
    i0, j0 = find_black_square(search_area, size=cell_size, error=0.3).__next__()

    # List of all answers grouped by question.
    answers = []
    j = j0
    for _ in range(n_questions):
        answers.append([])
        j += cell_size
        i = i0
        for __ in range(n_answers):
            i += cell_size
            answers[-1].append(test_square_color(search_area, i, j, cell_size, level=0.5))

    print("Answers:\n%s" % '\n'.join(str(a) for a in answers))

    return identifier, answers, student_number


def scan_all_pages(pics, config):
    for pic in pics:
        identifier, answers, student_number = scan_picture(pic, config)


def _pgm_from_matrix(matrix, squares, size):
    """"This tools generate a PGM file for debuging purpose.
    """
    with open("debug_squares_detection.pgm"):
        pass



#m = lire_image("carres.pbm")
#print(detect_all_squares(m, size=15))
