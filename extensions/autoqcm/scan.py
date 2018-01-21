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
from os.path import (isdir, isfile, join as joinpath, expanduser, abspath,
                     dirname, basename)
from os import listdir, mkdir
from shutil import rmtree
import subprocess
import tempfile
import argparse
import csv
import sys
from numpy import array, nonzero, transpose
from pylab import imread
from PIL import Image

# File `compilation.py` is in ../.., so we have to "hack" `sys.path` a bit.
script_path = dirname(abspath(sys._getframe().f_code.co_filename))
sys.path.insert(0, joinpath(script_path, '../..'))

from generate import generate_answers_and_score
from parameters import (SQUARE_SIZE_IN_CM, CELL_SIZE_IN_CM, MARGIN_LEFT_IN_CM,
                         MARGIN_RIGHT_IN_CM, MARGIN_TOP_IN_CM,
                         MARGIN_BOTTOM_IN_CM, PAPER_FORMAT, PAPER_FORMATS,
                        )
from compilation import compiler, make_file, join_files


def convert_png_to_gray(name):
    # Read from PNG or JPG file.
    m = imread(name)
    # m.shape[2] is 4 if there is an alpha channel (transparency), 3 else (RGB).
    print("Image data:", m)
    print("Image data shape:", m.shape)
    if len(m.shape) == 3: # Colored picture
        n = m.shape[2]
        assert n in (3, 4) # RGB or RGBA
        m = (m.sum(2) - (n - 3))/3
    assert len(m.shape) == 2
    # Return a grayscale picture, as a matrix.
    # Each pixel is represented by a float between 0.0 and 1.0,
    # where 0.0 stands for black (and so 1.0 stands for white).
    return m



def find_black_rectangle(matrix, width=50, height=50, error=0.30, gray_level=.4, mode='l', debug=False):
    """Detect a black rectangle of given size (in pixels) in matrix.

    The n*m matrix must contain only floats between 0 (white) and 1 (black).

    Optional parameters:
        - `error` is the ratio of white pixels allowed in the black square.
        - `gray_level` is the level above which a pixel is considered to be white.
           If it is set to 0, only black pixels will be considered black ; if it
           is close to 1 (max value), almost all pixels are considered black
           except white ones (for which value is 1.).
        - `mode` is either 'l' (picture is scanned line by line, from top to bottom)
           or 'c' (picture is scanned column by column, from left to right).

    Return a generator of (i, j) where i is line number and j is column number,
    indicating black squares top left corner.

    """
    # First, convert grayscale image to black and white.
    m = array(matrix, copy=False) < gray_level
    # Black pixels are represented by False, white ones by True.
    #pic_height, pic_width = m.shape
    per_line = (1 - error)*width
    per_col = (1 - error)*height
    goal = per_line*height
    to_avoid = []
    # Find a black pixel, starting from top left corner,
    # and scanning line by line (ie. from top to bottom).
    if mode == 'l':
        black_pixels = nonzero(m)
    elif mode == 'c':
        black_pixels = reversed(nonzero(transpose(array(m))))
    else:
        raise RuntimeError("Unknown mode: %s. Mode should be either 'l' or 'c'." % repr(mode))
    if debug:
        print(mode, black_pixels)
    for (i, j) in zip(*black_pixels):
        # Avoid to detect an already found square.
        if debug:
            print("Black pixel found at %s, %s" % (i, j))
            #~ color2debug(matrix, (i,j), (i + 2,j + 2), color=(255,0,255), fill=True)
        if any((li_min <= i <= li_max and co_min <= j <= co_max)
                for (li_min, li_max, co_min, co_max) in to_avoid):
            continue
        assert m[i, j] == 1
        total = m[i:i+height, j:j+width].sum()
#        print("Detection: %s found (minimum was %s)." % (total, goal))
        if total >= goal:
            #~ print("\nBlack square found at (%s,%s)." % (i, j))
            # Adjust detection if top left corner is a bit "damaged"
            # (ie. if some pixels are missing there), or if this pixel is
            # only an artefact before the square.
            if debug:
                color2debug(matrix, (i,j), (i + 2,j + 2), fill=True)
            i0 = i
            j0 = j
            # Note: limit adjustement range (in case there are two consecutive squares)
            for _i in range(50):
                horizontal = vertical = False
                # Horizontal adjustement:
                try:
                    while abs(j - j0) < error*width \
                        and (m[i:i+height, j+width+1].sum() > per_col > m[i:i+height, j].sum()):
                        j += 1
                        if debug:
                            print("j+=1")
                        horizontal = True
                except IndexError:
                    pass
                # If square was already shifted horizontally in one way, don't try
                # to shift it in the opposite direction.
                if not horizontal:
                    try:
                        while abs(j - j0) < error*width \
                            and m[i:i+height, j+width].sum() < per_col < m[i:i+height, j-1].sum():
                            j -= 1
                            if debug:
                                print("j-=1")
                            horizontal = True
                    except IndexError:
                        pass
                # Vertical adjustement:
                try:
                    while abs(i - i0) < error*height and m[i+height+1, j:j+width].sum() > per_line > m[i, j:j+width].sum():
                        i += 1
                        if debug:
                            print("i+=1")
                        vertical = True
                except IndexError:
                    pass
                try:
                    while abs(i - i0) < error*height and m[i+height, j:j+width].sum() < per_line < m[i-1, j:j+width].sum():
                        i -= 1
                        if debug:
                            print("i-=1")
                        vertical = True
                except IndexError:
                    pass
                if not (vertical or horizontal):
                    break
            else:
                print("Warning: adjustement of square position seems abnormally long... Skiping...")
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

            to_avoid.append((i - error*height - 1, i + height - 2, j - error*width - 1, j + width - 2))
            #~ print("Final position of this new square is (%s, %s)" % (i, j))
            #~ print("Forbidden areas are now:")
            #~ print(to_avoid)
            if debug:
                input('-- pause --')
            yield (i, j)


def find_black_square(matrix, size, **kw):
    return find_black_rectangle(matrix, width=size, height=size, **kw)


def detect_all_squares(matrix, size=50, error=0.30):
    return list(find_black_square(matrix, size=size, error=error))



def test_square_color(m, i, j, size, proportion=0.3, gray_level=.75, _debug=False):
    """Return True if square is black, False else.

    (i, j) is top left corner of the square, where i is line number
    and j is column number.
    `proportion` is the minimal proportion of black pixels the square must have
    to be considered black (`gray_level` is the level below which a pixel
    is considered black).
    """
    square = m[i:i+size, j:j+size] < gray_level
    if _debug:
        print("proportion of black pixels detected: %s (minimum required was %s)"
                                        % (square.sum()/size**2, proportion))
    # Test also the core of the square, since borders may induce false
    # positives if proportion is kept low (like default value).
    core = square[2:-2,2:-2]
    return square.sum() > proportion*size**2 and core.sum() > proportion*(size - 4)**2


def eval_square_color(m, i, j, size, proportion=0.3, gray_level=.75, _debug=False):
    """Return an indice of blackness, which is a float in range (0, 1).

    The indice is useful to compare several squares, and find the blacker one.
    Note that the core of the square is considered the more important part to assert
    blackness.

    (i, j) is top left corner of the square, where i is line number
    and j is column number.
    `proportion` is the minimal proportion of black pixels the square must have
    to be considered black (`gray_level` is the level below which a pixel
    is considered black).
    """
    square = m[i:i+size, j:j+size]
    # Test also the core of the square, since borders may induce false
    # positives if proportion is kept low (like default value).
    core = square[2:-2,2:-2]
    return 1 - (3*core.sum()/(size - 4)**2 + square.sum()/size**2)/4



def find_lonely_square(m, size, error):
    "Find a black square surrounded by a white area."
    s = size
    for i, j in find_black_square(m, s, error=0.4):
        # Test if all surrounding squares are white.
        # (If not, it could be a false positive, caused by a stain
        # or by some student writing.)
        if not any(test_square_color(m, i_, j_, s, proportion=0.5, gray_level=0.5)
                    for i_, j_ in [(i - s, j - s), (i - s, j), (i - s, j + s),
                                   (i, j - s), (i, j + s),
                                   (i + s, j - s), (i + s, j), (i + s, j + s)]):
            return i, j




def color2debug(array, from_=None, to_=None, color=(255, 0, 0), display=True, fill=False, _d={}):
    """Display picture with a red (by default) rectangle for debuging.

    `array` is an array containing the image data (image must be gray mode,
    each pixel represented by a float from 0 (black) to 1 (white).
    `from_` represent one corner of the red rectangle.
    `to_` represent opposite corner of the red rectangle.
    `color` is given as a RGB tuple ([0-255], [0-255], [0-255]).
    `fill` (True|False) indicates if the rectangle should be filled.

    Usage: color2debug((0,0), (200,10), color=(255, 0, 255))

    If you need to display `n` rectangles, call `color2debug()` with
    `display=False` for the first `n-1` rectangles, and then with
    `display=True` for the last rectangle.

    `_d` is used internally to store values between two runs, if display=False.

    NOTA:
    - `feh` must be installed.
      On Ubuntu/Debian: sudo apt-get install feh
    - Left-draging the picture with mouse inside feh removes bluring/anti-aliasing,
      making visual debugging a lot easier.
    """
    ID = id(array)
    if ID not in _d:
        # Load image only if not loaded previously.
        _d[ID] = Image.fromarray(255*array).convert('RGB')
    rgb = _d[ID]
    height, width = array.shape
    if from_ is not None:
        if to_ is None:
            to_ = from_
        i1, j1 = from_
        i2, j2 = to_
        if i2 is None:
            i2 = height - 1
        if j2 is None:
            j2 = width - 1
        pix = rgb.load()
        imin, imax = int(min(i1, i2)), int(max(i1, i2))
        jmin, jmax = int(min(j1, j2)), int(max(j1, j2))
        if fill:
            for i in range(imin, imax + 1):
                for j in range(jmin, jmax + 1):
                    pix[j, i] = color
        else:
            # left and right sides of rectangle
            for i in range(imin, imax + 1):
                for j in (jmin, jmax):
                    pix[j, i] = color
            # top and bottom sides of rectangle
            for j in range(jmin, jmax + 1):
                for i in (imin, imax):
                    pix[j, i] = color
    if display:
        with tempfile.TemporaryDirectory() as tmpdirname:
            path = joinpath(tmpdirname, 'test.png')
            rgb.save(path)
            subprocess.run(["feh", path])
            input('-- pause --')
        del _d[ID]





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
    n_questions = config['questions']
    n_answers = config['answers (max)']
    students = config['students']
    n_students = len(students)
    ids = config['ids']

    # ------------------------------------------------------------------
    #                          CALIBRATION
    # ------------------------------------------------------------------
    for i in range(1, 3):
        print("Calibration: step %s/2" % i)
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

        if i == 1:
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
    imin = i1 - square_size
    imax = i1 + int(2*square_size)
    try:
        i3, j3 = find_black_square(m[imin:imax,maxj:minj], size=square_size,
                                   error=0.3, mode='c', debug=False).__next__()
    except StopIteration:
        print("ERROR: Can't find identification band, displaying search area in red.")
        color2debug(m, (imin, minj), (imax, maxj))
        raise RuntimeError("Can't find identification band !")

    i3 += imin
    j3 += maxj
    #~ print("Identification band starts at (%s, %s)" % (i3, j3))
    #~ color2debug((i3, j3), (i3 + square_size, j3), color=(0,255,0), display=False)
    #~ color2debug((i3, j3), (i3, j3 + square_size), color=(0,255,0), display=False)

    identifier = 0
    # Test the color of the 15 following squares,
    # and interpret it as a binary number.
    j = j3
    for k in range(15):
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

    print("Identifier read: %s" % identifier)

    # Exclude the codebar and top squares from the search area.
    # If rotation correction was well done, we should have i1 ≃ i2 ≃ i3.
    # Anyway, it's safer to take the max of them.
    vpos = max(i1, i2, i3) + 2*square_size




    # ------------------------------------------------------------------
    #                  IDENTIFY STUDENT (OPTIONAL)
    # ------------------------------------------------------------------
    student_number = None
    student_name = "Unknown student!"


    # Read student name directly
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~

    if n_students:
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

    elif ids:
        digits = len(str(max(ids)))
        imin = round(int(vpos + 2*square_size))
        imax = round(int(vpos + (3.5 + digits)*square_size))
        height = digits*square_size
        #~ color2debug(m, (imin, 0), (imax, 1000), color=(0,120,255), display=False)
        search_area = m[imin:imax,:]
        i0, j0 = find_black_rectangle(search_area, width=square_size,
                                height=height, error=0.3, mode='c', debug=False).__next__()
        vpos = imin + height
        #~ color2debug(m, (imin + i0, j0), (imin + i0 + height, j0 + square_size), color=(0,255,0))
        n = 0
        for k in range(digits):
            i = int(round(i0 + k*f_square_size))
            # `vals` is a dict of potentially checked digits.
            # Format: {indice of blackness: digit}
            # The blackest of all the black cases of the row will be considered
            # checked by the student, as long as there is enough difference
            # between the blackest and the other black one.
            vals = []
            for d in range(10):
                j = int(round(j0 + (d + 1)*f_square_size))
                if test_square_color(search_area, i, j, square_size):
                    blackness = eval_square_color(search_area, i, j, square_size)
                    vals.append((blackness, d))
                    #~ color2debug((imin + i, j), (imin + i + square_size, j + square_size))
            if vals:
                vals.sort(reverse=True)
                # Test if there is enough difference between the blackest
                # and the second blackest (minimal difference was set empirically).
                if len(vals) == 1 or vals[0][0] - vals[1][0] > 0.3:
                    # The blackest one:
                    digit = vals[0][1]
                    n += digit*10**(digits - k - 1)
        if n in ids:
            print("Student ID:", n)
            student_name = ids[n]
        else:
            print("Warning: invalid student id '%s' !" % n)



    else:
        print("No students list.")

    print("Student name:", student_name)





    # ------------------------------------------------------------------
    #                      READ ANSWERS
    # ------------------------------------------------------------------
    # Detect the answers.
    f_cell_size = CELL_SIZE_IN_CM*pixels_per_cm
    cell_size = int(round(f_cell_size))
    search_area = m[vpos:,:]
    i0, j0 = find_black_square(search_area, size=cell_size, error=0.3).__next__()
    #~ color2debug((vpos + i0, j0), (vpos + i0 + cell_size, j0 + cell_size), display=True)

    # List of all answers grouped by question.
    # (So answers will be a matrix, each line corresponding to a question.)
    answers = []
    dj = 0
    flip = config['flip']
    for kj in range(n_questions):
        answers.append([])
        dj = int(round((kj + 1)*f_cell_size))
        di = 0
        for ki in range(n_answers):
            di = int(round((ki + 1)*f_cell_size))
            # Table can be flipped (lines <-> rows) to save space if there are
            # many answers proposed and few questions.
            if flip:
                i = i0 + dj
                j = j0 + di
            else:
                i = i0 + di
                j = j0 + dj

            # Remove borders of the square when testing,
            # since it may induce false positives.
            answers[-1].append(test_square_color(search_area, i + 5, j + 5, cell_size - 7, proportion=0.3, gray_level=0.65) or
                               test_square_color(search_area, i + 5, j + 5, cell_size - 7, proportion=0.4, gray_level=0.75))
            #~ if test_square_color(search_area, i, j, cell_size):
                #~ test_square_color(search_area, i + 5, j + 5, cell_size - 7, _debug=True)
                #~ color2debug((vpos + i, j), (vpos + i + cell_size, j + cell_size),display=False)
                #~ color2debug((vpos + i + 5, j + 5), (vpos + i + cell_size - 2, j + cell_size - 1),color=(0, 153, 0))

    #~ print("Answers:\n%s" % '\n'.join(str(a) for a in answers))
    print("Result of grid scanning:")
    rows = (answers if flip else zip(*answers))
    for row in rows:
        print(' '.join(('■' if checked else '□') for checked in row))


    correct_answers = config['answers'][identifier]

    # ------------------------------------------------------------------
    #                      CALCULATE SCORE
    # ------------------------------------------------------------------
    scores = []
    mode = config['mode']
    for i, (correct, proposed) in enumerate(zip(correct_answers, answers)):
        # Nota: most of the time, there should be only one correct answer.
        # Anyway, this code intends to deal with cases where there are more
        # than one correct answer too.
        # If mode is set to 'all', student must check *all* correct propositions ;
        # if not, answer will be considered incorrect. But if mode is set to
        # 'some', then student has only to check a subset of correct propositions
        # for his answer to be considered correct.
        proposed = {j for (j, b) in enumerate(proposed) if b}
        correct = set(correct)
        #~ print("proposed:", proposed, "correct answers:", correct)
        #~ input('-- pause --')
        if mode == 'all':
            ok = (correct == proposed)
        elif mode == 'some':
            ok = proposed and proposed.issubset(correct)
        else:
            raise RuntimeError('Invalid mode (%s) !' % mode)
        print(ok, proposed, correct)
        if ok:
            scores.append(config['correct'])
        elif not proposed:
            scores.append(config['skipped'])
        else:
            scores.append(config['incorrect'])

    score = sum(scores)
    print('Scores: ', scores, '->', score, '/', config['correct']*len(scores))

    return {'ID': identifier, 'answers': answers, 'name': student_name,
            'score': score, 'students': students, 'ids': ids}






def read_config(pth):
    def bool_(s):
        return s.lower() == 'true'
    cfg = {'answers': {}, 'students': [], 'ids': {}}
    parameters_types = {'mode': str, 'correct': float, 'incorrect': float,
                  'skipped': float, 'questions': int, 'answers (max)': int,
                  'flip': bool_, 'seed': int}
    ans = cfg['answers']
    with open(pth) as f:
        section = 'parameters'
        for line in f:
            try:
                if line.startswith('*** ANSWERS (TEST '):
                    num = int(line[18:-6])
                    ans[num] = []
                    section = 'answers'
                elif line.startswith('*** STUDENTS LIST ***'):
                    section = 'students'
                    students = cfg['students']
                elif line.startswith('*** IDS LIST ***'):
                    section = 'ids'
                    ids = cfg['ids']
                else:
                    if section == 'parameters':
                        key, val =  line.split(':')
                        key = key.strip().lower()
                        val = parameters_types[key](val.strip())
                        cfg[key] = val
                    elif section == 'answers':
                        q, correct_ans = line.split(' -> ')
                        # There may be no answers, so test if string is empty.
                        if correct_ans.strip():
                            ans[num].append([int(n) - 1 for n in correct_ans.split(',')])
                        else:
                            ans[num].append([])
                        assert len(ans[num]) == int(q), ('Incorrect question number: %s' % q)
                    elif section == 'students':
                        students.append(line.strip())
                    elif section == 'ids':
                        num, name = line.split(':', 1)
                        ids[int(num)] = name.strip()
                    else:
                        raise NotImplementedError('Unknown section: %s !' % section)

            except Exception:
                print("Error while parsing this line: " + repr(line))
                raise
    return cfg


def search_by_extension(directory, ext):
    """Search for a file with extension `ext` in given directory.

    Search is NOT case sensible.
    If no or more than one file is found, an error is raised.
    """
    ext = ext.lower()
    names = [name for name in listdir(directory) if name.lower().endswith(ext)]
    if not names:
        raise FileNotFoundError('No `%s` file found in that directory (%s) ! '
                                % (ext, directory))
    elif len(names) > 1:
        raise RuntimeError('Several `%s` file found in that directory (%s) ! '
            'Keep one and delete all others (or rename their extensions).'
            % (ext, directory))
    return joinpath(directory, names[0])


def extract_pictures(pdf_path, dest, page=None):
    "Extract all pictures from pdf file in given `dest` directory. "
    print('Extracting all images from pdf, please wait...')
    cmd = ["pdfimages", "-all", pdf_path, joinpath(dest, 'pic')]
    if page is not None:
        p = str(page)
        cmd = cmd[:1] + ['-f', p, '-l', p] + cmd[1:]
    #~ print(cmd)
    subprocess.run(cmd, stdout=subprocess.PIPE)

def convert_pdf_to_png(pdf_path, dest, page=None):
    print('Convert PDF to PNG, please wait...')
    cmd = ['gs', '-dNOPAUSE', '-dBATCH', '-sDEVICE=jpeg', '-r200',
           '-sOutputFile=' + joinpath(dest, 'page-%03d.jpg'), pdf_path]
    if page is not None:
        cmd = cmd[:1] + ["-dFirstPage=%s" % page, "-dLastPage=%s" % page] + cmd[1:]
    subprocess.run(cmd, stdout=subprocess.PIPE)


def number_of_pages(pdf_path):
    "Return the number of pages of the pdf."
    cmd = ["pdfinfo", pdf_path]
    # An example of pdfinfo output:
    # ...
    # JavaScript:     no
    # Pages:          19
    # Encrypted:      no
    # ...
    l = subprocess.run(cmd, stdout=subprocess.PIPE).stdout.decode('utf-8').split()
    return int(l[l.index('Pages:') + 1])


def read_name_manually(pic_path, ids=None, msg='', default=None):
    if msg:
        decoration = max(len(line) for line in msg.split('\n'))*'-'
        print(decoration)
        print(msg)
        print(decoration)
    print('Please read manually the name, then enter it below.')
    subprocess.run(["display", "-resize", "1920x1080", pic_path])
    #TODO: use first letters of students name to find student.
    #(ask again if not found, or if several names match first letters)
    while True:
        name = input('Student name or ID:')
        if not name:
            if default is None:
                continue
            name = default
        name = name.strip()
        if name.isdigit() and ids:
            try:
                name = ids[int(name)]
            except KeyError:
                print('Unknown ID.')
                continue
        print("Name: %s" % name)
        if input("Is it correct ? (Y/n)") in ("N", "n"):
            continue
        if name:
            break
    return name


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Extract information from numerised tests.")
    parser.add_argument('path', help=("Path to a directory which must contain "
                        "a .autoqcm.config file and a .scan.pdf file "
                        "(alternatively, this path may point to any file in this folder)."))
    group = parser.add_mutually_exclusive_group()
    # Following options can't be used simultaneously.
    group.add_argument("-p", "--page", metavar="P", type=int,
                                        help="Read only page P of pdf file.")
    group.add_argument("-s", "--skip-pages", metavar="P", type=int, nargs='+', default=[],
                                        help="Skip page P of pdf file.")
    parser.add_argument("-n", "--names", metavar="CSV_FILENAME", type=str,
                                        help="Read names from file CSV_FILENAME.")
    parser.add_argument("-P", "--print", action='store_true',
                        help='Print scores and solutions on default printer.')
    parser.add_argument("-m", '-M', "--mail", metavar="CSV_file",
                                                help='Mail scores and solutions.')
    parser.add_argument("--reset", action="store_true", help='Delete `scan` directory.')
    parser.add_argument("-d", "--dir", type=str,
                            help='Specify a directory with write permission.')
    parser.add_argument("--hide-scores", action='store_true',
                help="Print only answers, not scores, in generated pdf files.")
    args = parser.parse_args()


    if args.path.endswith('.png') or args.path.endswith('.jpg'):
        # This is used for debuging (it allows to test pages one by one).
        configfile = search_by_extension(dirname(abspath(args.path)), '.autoqcm.config')
        config = read_config(configfile)
        print(config)
        data = scan_picture(abspath(expanduser(args.path)), config)
        print(data)

    else:
        # This is the usual case: tests are stored in only one big pdf file ;
        # we will process all these pdf pages.

        # First, detect pdf file.
        # NB: file extension must be `.scan.pdf`.
        DIR = abspath(expanduser(args.path))
        if not isdir(DIR):
            DIR = dirname(DIR)
            if not isdir(DIR):
                raise FileNotFoundError('%s does not seem to be a directory !' % DIR)

        # Directory tree:
        # scan/
        # scan/pic -> pictures extracted from the pdf
        # scan/cfg/more_infos.csv -> missing students names.
        # scan/scores.csv
        SCAN_DIR = joinpath(args.dir or DIR, 'scan')
        CFG_DIR = joinpath(SCAN_DIR, 'cfg')
        PIC_DIR = joinpath(SCAN_DIR, 'pic')
        PDF_DIR = joinpath(SCAN_DIR, 'pdf')

        if args.reset and isdir(SCAN_DIR):
            rmtree(SCAN_DIR)

        for directory in (SCAN_DIR, CFG_DIR, PIC_DIR, PDF_DIR):
            print(directory)
            if not isdir(directory):
                mkdir(directory)

        base_name = basename(search_by_extension(DIR, '.ptyx'))[:-5]
        scan_pdf_path = search_by_extension(DIR, '.scan.pdf')
        scores_pdf_path = joinpath(PDF_DIR, '%s-scores' % base_name)
        data_path = joinpath(CFG_DIR, 'data.csv')

        # Print scores and solutions (a first scan must have been done earlier).
        if args.print:
            #TODO: test this section.
            if not isfile(data_path):
                raise RuntimeError('Data file not found ! Run ./scan.py once before.')
            print('\nPREPARING TO PRINT SCORES...')
            print("Insert test papers in printer (to print score and solutions on other side).")
            with open(data_path, 'r', newline='') as csvfile:
                reader = csv.reader(csvfile)
                for i, row in enumerate(reader):
                    identifier, name, score = row
                    print('Student:', name, '(subject number: %s, score %s)' % (identifier, score))
                    input('-pause- (Press ENTER to process, CTRL^C to quit)')
                    subprocess.run(["lp", "-P %s" % (i + 1), "-o sides=one-sided",
                                    scores_pdf_path], stdout=subprocess.PIPE)
            sys.exit()
        elif args.mail:
            #TODO
            pass

        # Read configuration file.
        configfile = search_by_extension(DIR, '.autoqcm.config')
        config = read_config(configfile)
        #~ print(config)

        # Maximal score = (number of questions)x(score when answer is correct)
        max_score = len(iter(config['answers'].values()).__next__())*config['correct']

        if args.names is not None:
            with open(args.names, newline='') as csvfile:
                names = [' '.join(row) for row in csv.reader(csvfile) if row and row[0]]


        # Extract all images from pdf.
        if len(listdir(PIC_DIR)) != number_of_pages(scan_pdf_path):
            extract_pictures(scan_pdf_path, PIC_DIR, args.page)

        EXTS = ('.jpg', '.jpeg', '.png')
        pics = listdir(PIC_DIR)
        if not all(any(f.endswith(ext) for ext in EXTS) for f in pics):
            rmtree(PIC_DIR)
            mkdir(PIC_DIR)
            convert_pdf_to_png(scan_pdf_path, PIC_DIR, args.page)

        # Read manually entered informations (if any).
        more_infos = {} # sheet_id: name
        cfg_path = joinpath(CFG_DIR, 'more_infos.csv')
        if isfile(cfg_path):
            with open(cfg_path, 'r', newline='') as csvfile:
                reader = csv.reader(csvfile)
                for row in reader:
                    sheet_id, name = row
                    more_infos[int(sheet_id)] = name
                print("Retrieved infos:", more_infos)


        # Extract informations from the pictures.
        #~ scores = {} # {name: score}
        #~ pages = {} # {name: page}
        #~ pics = {} # {name: pic}
        #~ sheets = {} # {name: sheet ID}

        index = {} # {name: index} -> used to retrieve data associated with a name.
        all_data = []
        exts = ('.jpg', '.jpeg', '.png')
        pic_list = sorted(f for f in listdir(PIC_DIR)
                        if any(f.lower().endswith(ext) for ext in exts))
        for i, pic in enumerate(pic_list):
            if args.page is not None and args.page != i + 1:
                continue
            if i + 1 in args.skip_pages:
                continue
            print('-------------------------------------------------------')
            print('Page', i + 1)
            print('File:', pic)
            # Extract data from image
            pic_path = joinpath(PIC_DIR, pic)
            data = scan_picture(pic_path, config)
            # data format: {'ID': sheet ID (int),
            #               'answers': answers (list),
            #               'name': student name (str),
            #               'score': score (float),
            #               'students': students names (list),
            #               'ids': students ID (dict)}
            all_data.append(data)
            #~ sheet_id, _, name, score, students, ids = data
            # Manually entered information must prevail:
            name = more_infos.get(data['ID'], data['name'])
            if args.names is None:
                if name == "Unknown student!":
                    name = read_name_manually(pic_path, data['ids'], msg=name)
                    more_infos[data['ID']] = name
                if name in index:
                    print('Page %s: %s' % (index[name] + 1, name))
                    print('Page %s: %s' % (i + 1, name))
                    msg = 'Error : 2 tests for same student (%s) !\n' % name
                    msg += "Write nothing if a name is correct."
                    i1 = index.pop(name)
                    old_data = all_data[i1]
                    pic_path1 = joinpath(PIC_DIR, old_data['pic'])
                    name1 = read_name_manually(pic_path1, data['ids'], msg, default=name)
                    more_infos[old_data['ID']] = name1
                    index[name1] = i1
                    name = read_name_manually(pic_path, data['ids'], default=name)
                    more_infos[data['ID']] = name

            else:
                if not names:
                    raise RuntimeError('Not enough names in `%s` !' % args.names)
                name = names.pop(0)
                print('Name:', name)
            data['name'] = name
            data['pic'] = pic
            index[name] = i
            # `names` dict is used to find data associated with a given name.
            assert all_data[index[name]]['name'] == name
            #~ scores[name] = score
            #~ pages[name] = i + 1
            #~ pics[name] = pic
            #~ sheets[name] = sheet_id
            print("Score: %s/%s" % (data['score'], max_score))

        # Store manually entered information (may be useful
        # if scan.py has to be run again later).
        with open(cfg_path, 'w', newline='') as csvfile:
            writerow = csv.writer(csvfile).writerow
            for sheet_id, name in more_infos.items():
                writerow([str(sheet_id), name])

        if args.names is not None and names:
            # Names list should be empty !
            raise RuntimeError('Too many names in `%s` !' % args.names)


        # Generate CSV file with results.
        scores = {data['name']: data['score'] for data in all_data}
        #~ print(scores)
        scores_path = joinpath(SCAN_DIR, 'scores.csv')
        print('SCORES (/%s):' % max_score)
        with open(scores_path, 'w', newline='') as csvfile:
            writerow = csv.writer(csvfile).writerow
            for name in sorted(scores):
                print(' - %s: %s' % (name, scores[name]))
                writerow([name, scores[name]])
        print("Results stored in %s." % scores_path)



        # Generate pdf files, with the score and the table of correct answers for each test.
        pdf_paths = []
        for data in all_data:
            #~ identifier, answers, name, score, students, ids
            ID = data['ID']
            name = data['name']
            score = data['score']
            path = joinpath(PDF_DIR, '%s-%s-corr.score' % (base_name, ID))
            pdf_paths.append(path)
            print('Generating pdf file for student %s (subject %s, score %s)...'
                                                    % (name, ID, score))
            latex = generate_answers_and_score(config, name, ID,
                            (score if not args.hide_scores else None), max_score)
            make_file(path, plain_latex=latex,
                                remove=True,
                                formats=['pdf'],
                                quiet=True,
                                )
        join_files(scores_pdf_path, pdf_paths, remove_all=True, compress=True)

        # Generate an hidden CSV file for printing or mailing results later.
        with open(data_path, 'w', newline='') as csvfile:
            writerow = csv.writer(csvfile).writerow
            for data in all_data:
                #~ (identifier, answers, name, score, students, ids)
                writerow([data['ID'], data['name'], data['score']])
        print("Data file generated for printing or mailing later.")





#m = lire_image("carres.pbm")
#print(detect_all_squares(m, size=15))
