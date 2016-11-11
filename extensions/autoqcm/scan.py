#!/usr/bin/env python3

# --------------------------------------
#                  Scan
#     Extract info from numerised tests
# --------------------------------------
#    PTYX
#    Python LaTeX preprocessor
#    Copyright (C) 2009-2016  Nicolas Pourcelot
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA


from math import atan, degrees
import argparse

from numpy import array#, apply_along_axis
from pylab import imread
#~ from PIL import Image


from parameters import SQUARE_SIZE_IN_CM, CELL_SIZE_IN_CM




def convert_png_to_gray(name):
    # Read from PNG file.
    m = imread(name)
    # m.shape[2] is 4 if there is an alpha channel (transparency), 3 else (RGB).
    n = m.shape[2]
    assert n in (3, 4)
    m = (m.sum(2) - (n - 3))/3
    return m



def find_black_square(matrix, size=50, error=0.30, gray_level=.4):
    """Detect a black square of given size (edge in pixels) in matrix.

    The matrix should contain only 1 (black) and 0 (white).

    Optional parameters:
        - `error` is the ratio of white pixels allowed is the black square.
        - `gray_level` is the level above which a pixel is considered to be white.
           If it is set to 0, only black pixels will be considered black ; if it
           is close to 1 (max value), almost all pixels are considered black
           except white ones (for which value is 1.).

    Return a generator of (i, j) where i is line number and j is column number,
    indicating black squares top left corner.

    """
    m = array(matrix, copy=False) < gray_level
    # Black pixels are represented by False, white ones by True.
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
                try:
                    while abs(j - j0) < error*size \
                        and (m[i:i+size, j+size+1].sum() > per_line > m[i:i+size, j].sum()):
                        j += 1
                        print("j+=1")
                        horizontal = True
                except IndexError:
                    pass
                # If square was already shifted horizontally in one way, don't try
                # to shift it in the opposite direction.
                if not horizontal:
                    try:
                        while abs(j - j0) < error*size \
                            and m[i:i+size, j+size].sum() < per_line < m[i:i+size, j-1].sum():
                            j -= 1
                            print("j-=1")
                            horizontal = True
                    except IndexError:
                        pass
                # Vertical adjustement:
                try:
                    while abs(i - i0) < error*size and m[i+size+1, j:j+size].sum() > per_line > m[i, j:j+size].sum():
                        i += 1
                        print("i+=1")
                        vertical = True
                    while abs(i - i0) < error*size and m[i+size, j:j+size].sum() < per_line < m[i-1, j:j+size].sum():
                        i -= 1
                        print("i-=1")
                        vertical = True
                except IndexError:
                        pass
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
            #~ print("Forbidden areas are now:")
            #~ print(to_avoid)
            yield (i, j)





def detect_all_squares(matrix, size=50, error=0.30):
    return list(find_black_square(matrix, size=size, error=error))



def test_square_color(m, i, j, size, proportion=0.5, gray_level=.75):
    """Return True if square is black, False else.

    (i, j) is top left corner of the square, where i is line number
    and j is column number.
    level is the minimal proportion of black pixels the square must have
    to be considered black (gray_level is the level below which a pixel
    is considered black).
    """
    square = m[i:i+size, j:j+size] < gray_level
    return square.sum() > proportion*size**2


def read_config(pth):
    cfg = {'answers': {}, 'students': []}
    ans = cfg['answers']
    with open(pth) as f:
        cfg['mode'] = f.readline()[6:-1]
        cfg['correct'] = float(f.readline()[9:])
        cfg['incorrect'] = float(f.readline()[11:])
        cfg['skipped'] = float(f.readline()[9:])
        cfg['n_questions'] = int(f.readline()[11:])
        cfg['n_max_answers'] = int(f.readline()[15:])
        for line in f:
            try:
                if line.startswith('*** ANSWERS (TEST '):
                    num = int(line[18:-6])
                    ans[num] = []
                elif line.startswith('*** STUDENTS LIST ***'):
                    break
                else:
                    q, correct_ans = line.split(' -> ')
                    ans[num].append([int(n) - 1 for n in correct_ans.split(',')])
            except Exception:
                print("Error while parsing this line: " + repr(line))
                raise
        students = cfg['students']
        for line in f:
            students.append(line.strip())
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
        m = convert_png_to_gray(m)
    if isinstance(config, str):
        config = read_config(config)
    n_questions = config['n_questions']
    n_answers = config['n_max_answers']
    students = config['students']
    n_students = len(students)

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

    #~ print("Squares list:\n" + str(detect_all_squares(m, square_size, 0.5)))

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

    i3, j3 = find_black_square(m[:maxi,maxj:minj], size=square_size, error=0.3).__next__()
    j3 += maxj
    print("Identification band starts at (%s, %s)" % (i3, j3))

    identifier = 0
    # Test the color of the 15 following squares,
    # and interpret it as a binary number.
    j = j3
    for k in range(15):
        j = int(round(j3 + (k + 1)*f_square_size))
        if test_square_color(m, i3, j, square_size, proportion=0.5, gray_level=0.5):
            print((k, (i3, j)), " -> black")
            identifier += 2**k
        else:
            print((k, (i3, j)), " -> white")

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
        i, j0 = find_black_square(search_area, size=square_size, error=0.3).__next__()

        l = []
        for k in range(1, n_students + 1):
            j = int(round(j0 + 2*k*f_square_size))
            l.append(test_square_color(search_area, i, j, square_size))

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
    f_cell_size = CELL_SIZE_IN_CM*pixels_per_cm
    cell_size = int(round(f_cell_size))
    search_area = m[vpos:,:]
    i0, j0 = find_black_square(search_area, size=cell_size, error=0.3).__next__()

    # List of all answers grouped by question.
    answers = []
    j = j0
    for kj in range(n_questions):
        answers.append([])
        j = int(round(j0 + (kj + 1)*f_cell_size))
        i = i0
        for ki in range(n_answers):
            i = int(round(i0 + (ki + 1)*f_cell_size))
            answers[-1].append(test_square_color(search_area, i, j, cell_size))

    print("Answers:\n%s" % '\n'.join(str(a) for a in answers))

    correct_answers = config['answers'][identifier]

    scores = []
    mode = config['mode']
    for i, (correct, proposed) in enumerate(zip(correct_answers, answers)):
        # Nota: most of the time, there should be only one correct answer.
        # This code also deals with cases where there are more than one correct
        # though.
        # If mode is set to 'all', student must check *all* correct propositions,
        # if not answer will be considered as incorrect. But if mode is set to
        # 'some', then student has only to check a subset of correct propositions
        # for his answer to be considered correct.
        proposed = {j for (j, b) in enumerate(proposed) if b}
        correct = set(correct)
        if mode == 'all':
            ok = (correct == proposed)
        elif mode == 'some':
            ok = proposed.issubset(correct)
        else:
            raise RuntimeError('Invalid mode (%s) !' % mode)
        if ok:
            scores.append(config['correct'])
        elif not proposed:
            scores.append(config['skipped'])
        else:
            scores.append(config['incorrect'])
    print('Scores: ', scores)
    score = sum(scores)


    return identifier, answers, student_number, score


def scan_all_pages(pics, config):
    for pic in pics:
        identifier, answers, student_number = scan_picture(pic, config)


def _pgm_from_matrix(matrix, squares, size):
    """"This tools generate a PGM file for debuging purpose.
    """
    with open("debug_squares_detection.pgm"):
        pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Extract information from numerised tests.")
    parser.add_argument('configfile')
    parser.add_argument('filenames', nargs='+')
    args = parser.parse_args()
    configfile = args.configfile
    if configfile.endswith('.ptyx'):
        configfile += '.autoqcm.config'
    config = read_config(configfile)
    print(config)
    for filename in args.filenames:
        print(scan_picture(filename, config))

        #TODO: if image format is multipage PDF, use `pdfimages -all` to extract images from it.

#m = lire_image("carres.pbm")
#print(detect_all_squares(m, size=15))
