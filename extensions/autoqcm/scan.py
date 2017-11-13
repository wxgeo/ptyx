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
from os.path import isdir, join as joinpath, expanduser, abspath, dirname, basename
from os import listdir
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
    # Read from PNG file.
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



def find_black_square(matrix, size=50, error=0.30, gray_level=.4, mode='l'):
    """Detect a black square of given size (edge in pixels) in matrix.

    The n*m matrix must contain only floats between 0 (white) and 1 (black).

    Optional parameters:
        - `error` is the ratio of white pixels allowed in the black square.
        - `gray_level` is the level above which a pixel is considered to be white.
           If it is set to 0, only black pixels will be considered black ; if it
           is close to 1 (max value), almost all pixels are considered black
           except white ones (for which value is 1.).
        - `mode` is either 'l' (picture is scanned line by line) or 'c' (picture
           is scanned column by column).

    Return a generator of (i, j) where i is line number and j is column number,
    indicating black squares top left corner.

    """
    # First, convert grayscale image to black and white.
    m = array(matrix, copy=False) < gray_level
    # Black pixels are represented by False, white ones by True.
    height, width = m.shape
    per_line = (1 - error)*size
    goal = per_line*size
    to_avoid = []
    # Find a black pixel, starting from top left corner,
    # and scanning line by line (ie. from top to bottom).
    if mode == 'l':
        black_pixels = nonzero(m)
    elif mode == 'c':
        black_pixels = reversed(nonzero(transpose(array(m))))
    else:
        raise RuntimeError("Unknown mode: %s. Mode should be either 'l' or 'c'." % repr(mode))
    for (i, j) in zip(*black_pixels):
        #print("Black pixel found at %s, %s" % (i, j))
        # Avoid to detect an already found square.
        if any((li_min <= i <= li_max and co_min <= j <= co_max)
                for (li_min, li_max, co_min, co_max) in to_avoid):
            continue
        assert m[i, j] == 1
        total = m[i:i+size, j:j+size].sum()
#        print("Detection: %s found (minimum was %s)." % (total, goal))
        if total >= goal:
            #~ print("\nBlack square found at (%s,%s)." % (i, j))
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
                        #~ print("j+=1")
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
                            #~ print("j-=1")
                            horizontal = True
                    except IndexError:
                        pass
                # Vertical adjustement:
                try:
                    while abs(i - i0) < error*size and m[i+size+1, j:j+size].sum() > per_line > m[i, j:j+size].sum():
                        i += 1
                        #~ print("i+=1")
                        vertical = True
                    while abs(i - i0) < error*size and m[i+size, j:j+size].sum() < per_line < m[i-1, j:j+size].sum():
                        i -= 1
                        #~ print("i-=1")
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

            to_avoid.append((i - error*size - 1, i + size - 2, j - error*size - 1, j + size - 2))
            #~ print("Final position of this new square is (%s, %s)" % (i, j))
            #~ print("Forbidden areas are now:")
            #~ print(to_avoid)
            yield (i, j)




def find_black_rectangle(matrix, width=50, height=50, error=0.30, gray_level=.4, mode='l'):
    """Detect a black rectangle of given size (in pixels) in matrix.

    The n*m matrix must contain only floats between 0 (white) and 1 (black).

    Optional parameters:
        - `error` is the ratio of white pixels allowed in the black square.
        - `gray_level` is the level above which a pixel is considered to be white.
           If it is set to 0, only black pixels will be considered black ; if it
           is close to 1 (max value), almost all pixels are considered black
           except white ones (for which value is 1.).
        - `mode` is either 'l' (picture is scanned line by line) or 'c' (picture
           is scanned column by column).

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
    for (i, j) in zip(*black_pixels):
        #print("Black pixel found at %s, %s" % (i, j))
        # Avoid to detect an already found square.
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
                        #~ print("j+=1")
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
                            #~ print("j-=1")
                            horizontal = True
                    except IndexError:
                        pass
                # Vertical adjustement:
                try:
                    while abs(i - i0) < error*height and m[i+height+1, j:j+width].sum() > per_line > m[i, j:j+width].sum():
                        i += 1
                        #~ print("i+=1")
                        vertical = True
                    while abs(i - i0) < error*height and m[i+height, j:j+width].sum() < per_line < m[i-1, j:j+width].sum():
                        i -= 1
                        #~ print("i-=1")
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









def scan_picture(filename, config):
    """Scan picture and return page identifier and list of answers for each question.

    - filename is a path pointing to a PNG file.
    - config is either a path poiting to a config file, or a dictionnary
    containing the following keys:
      * n_questions is the number of questions
      * n_answers is the number of answers per question.
      * n_students is the number of students

    Return an integer and a list of lists of booleans.
    """

    def color2debug(from_=None, to_=None, color=(255, 0, 0), display=True, fill=False, _d={}):
        """Display picture with a red (by default) rectangle for debuging.

        `from_` represent one corner of the red rectangle.
        `to_` represent opposite corner of the red rectangle.
        `color` is given as a RGB tuple ([0-255], [0-255], [0-255]).
        `fill` (True|False) indicates if the rectangle should be filled.

        Usage: color2debug((0,0), (200,10), color=(255, 0, 255))

        If you need to display `n` rectangles, call `color2debug()` with
        `display=False` for the first `n-1` rectangles, and then with
        `display=True` for the last rectangle.

        `_d` is used internally to store values between two runs, if display=False.
        """
        if not _d.get('rgb'):
            _d['rgb'] = pic.convert('RGB')
        rgb = _d['rgb']
        if from_ is not None:
            if to_ is None:
                to_ = from_
            pix = rgb.load()
            imin, imax = int(min(from_[0], to_[0])), int(max(from_[0], to_[0]))
            jmin, jmax = int(min(from_[1], to_[1])), int(max(from_[1], to_[1]))
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
                subprocess.run(["display", path])
                input('-- pause --')
            del _d['rgb']


    # Convert to grayscale picture.
    pic = Image.open(filename).convert('L')
    m = array(pic)/255.
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
        maxi = maxj = int(round(2*(1 + SQUARE_SIZE_IN_CM)*dpi/2.54))
        maxj0 = maxj
        # First, search the top left black square.
        while True:
            #~ color2debug((0, 0), (maxi, maxj), color=(0,255,0), display=True)
            try:
                #~ i1, j1 = find_black_square(m[:maxi,:maxj], size=square_size, error=0.5).__next__()
                i1, j1 = find_lonely_square(m[:maxi,:maxj], size=square_size, error=0.5)
                #~ color2debug((i1, j1), (i1 + square_size, j1 + square_size), color=(255,255,0), display=True)
                break
            except StopIteration:
                # Top square not found.
                # Expand search area, mostly vertically (expanding to much
                # horizontally may induce false positives, because of the QR code).
                print('Adjusting search area...')
                maxi += square_size
                if maxj < maxj0 + 4*square_size:
                    maxj += maxj + square_size//2

        # Search now for the top right black square.
        minj = int(round((20 - 2*(1 + SQUARE_SIZE_IN_CM))*dpi/2.54))
        i2, j2 = find_lonely_square(m[:maxi,minj:], size=square_size, error=0.5)
        j2 += minj

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
        i3, j3 = find_black_square(m[imin:imax,maxj:minj], size=square_size, error=0.3, mode='c').__next__()
    except StopIteration:
        print("ERROR: Can't find identification band, displaying search area in red.")
        color2debug((imin, minj), (imax, maxj))
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
        #~ color2debug((imin, 0), (imax, 1000), color=(0,120,255))
        search_area = m[imin:imax,:]
        i0, j0 = find_black_rectangle(search_area, width=square_size,
                                height=height, error=0.3, mode='c').__next__()
        vpos = imin + height
        #~ color2debug((imin + i0, j0), (imin + i0 + height, j0 + square_size), color=(0,255,0), display=False)
        n = 0
        for k in range(digits):
            i = int(round(i0 + k*f_square_size))
            # `vals` is a dict of potentially checked digits.
            # Format: {indice of blackness: digit}
            # The blackest of all the cases of the row will be considered
            # checked by the student.
            vals = {}
            for d in range(10):
                j = int(round(j0 + (d + 1)*f_square_size))
                if test_square_color(search_area, i, j, square_size):
                    blackness = eval_square_color(search_area, i, j, square_size)
                    vals[blackness] = d
                    #~ color2debug((imin + i, j), (imin + i + square_size, j + square_size))
            if vals:
                digit = vals[max(vals)]
                n += digit*10**(digits - k - 1)
        print("Student ID:", n)
        student_name = ids[n]



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
    print('Scores: ', scores)
    score = sum(scores)

    return identifier, answers, student_name, score



def read_config(pth):
    cfg = {'answers': {}, 'students': [], 'ids': {}}
    parameters_types = {'mode': str, 'correct': float, 'incorrect': float,
                  'skipped': float, 'questions': int, 'answers (max)': int,
                  'flip': bool, 'seed': int}
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
                                        help="Read only page P of pdf file.")
    parser.add_argument("-n", "--names", metavar="CSV_FILENAME", type=str,
                                        help="Read names from file CSV_FILENAME.")
    parser.add_argument("-P", "--print", action='store_true', help='Print scores and solutions on default printer.')
    parser.add_argument("-m", '-M', "--mail", metavar="CSV_file", help='Mail scores and solutions.')
    args = parser.parse_args()


    def search_by_extension(directory, ext):
        names = [name for name in listdir(directory) if name.endswith(ext)]
        if not names:
            raise FileNotFoundError('No `%s` file found in that directory (%s) ! '
                                    % (ext, directory))
        elif len(names) > 1:
            raise RuntimeError('Several `%s` file found in that directory (%s) ! '
                'Keep one and delete all others (or rename their extensions).'
                % (ext, directory))
        return joinpath(directory, names[0])

    if args.path.endswith('.png'):
        # This is used for debuging (it allows to test pages one by one).
        configfile = search_by_extension(dirname(args.path), '.autoqcm.config')
        config = read_config(configfile)
        print(config)
        data = scan_picture(abspath(expanduser(args.path)), config)
        print(data)

    else:
        # This is the usual case: tests are stored in only one big pdf file ;
        # we will process all these pdf pages.

        # First, detect pdf file.
        # NB: file extension must be `.scan.pdf`.
        directory = abspath(expanduser(args.path))
        if not isdir(directory):
            directory = dirname(directory)
            if not isdir(directory):
                raise FileNotFoundError('%s does not seem to be a directory !' % directory)


        # Print scores and solutions (a first scan must have been done earlier).
        if args.print:
            csvname = joinpath(directory, '.%s.scan.csv' % basename(scanpdf[:-9]))
            print('\nPREPARING TO PRINT SCORES...')
            print("Insert test papers in printer (to print score and solutions on other side).")
            with open(csvname, 'r', newline='') as csvfile:
                reader = csv.reader(csvfile)
                for row in reader:
                    identifier, name, score = row
                    print('Student:', name, '(subject number: %s, score %s)' % (identifier, score))
                    input('-pause- (Press ENTER to process, CTRL^C to quit)')
                    subprocess.run(["lp", "-P %s" % (i + 1), "-o sides=one-sided",
                                    "%s.pdf" % output_name], stdout=subprocess.PIPE)
            sys.exit()
        elif args.mail:
            pass

        scanpdf = search_by_extension(directory, '.scan.pdf')

        # Read configuration file.
        configfile = search_by_extension(directory, '.autoqcm.config')
        config = read_config(configfile)
        #~ print(config)

        # Maximal score = (number of questions)x(score when answer is correct)
        max_score = len(iter(config['answers'].values()).__next__())*config['correct']

        if args.names is not None:
            with open(args.names, newline='') as csvfile:
                names = [' '.join(row) for row in csv.reader(csvfile) if row and row[0]]

        names_manually_modified = False
        # Extract all images from pdf.
        with tempfile.TemporaryDirectory() as tmp_path:
            #tmp_path = '/home/nicolas/.tmp/scan'
            print(scanpdf, tmp_path)
            print('Extracting all images from pdf, please wait...')
            cmd = ["pdfimages", "-all", scanpdf, joinpath(tmp_path, 'pic')]
            if args.page is not None:
                p = str(args.page)
                cmd = cmd[:1] + ['-f', p, '-l', p] + cmd[1:]
            result = subprocess.run(cmd, stdout=subprocess.PIPE)
            scores = {}
            all_data = []
            for i, pic in enumerate(sorted(listdir(tmp_path))):
                if i + 1 in args.skip_pages:
                    continue
                print('-------------------------------------------------------')
                print('Page', i + 1)
                # Extract data from image
                data = list(scan_picture(joinpath(tmp_path, pic), config))
                all_data.append(data)
                name, score = data[2:]
                if args.names is None:
                    if name == "Unknown student!":
                        print('----------------')
                        print(name)
                        print('----------------')
                        print('Please read manually the name and enter it below:')
                        subprocess.run(["display", "-resize", "1920x1080", joinpath(tmp_path, pic)])
                        name = input('Student name:')
                        names_manually_modified = True
                    if name in scores:
                        raise RuntimeError('2 tests for same student (%s) !' % name)
                else:
                    if not names:
                        raise RuntimeError('Not enough names in `%s` !' % args.names)
                    name = names.pop(0)
                data[2] = name
                scores[name] = score
                print("Score: %s/%s" % (data[3], max_score))

        if args.names is not None and names:
            # Names list should be empty !
            raise RuntimeError('Too many names in `%s` !' % args.names)

        if names_manually_modified:
            # Generate CSV file with names.
            # (names will be in the same order than scanned files)
            csvname = scanpdf[:-9] + '.names.csv'
            with open(csvname, 'w', newline='') as csvfile:
                writerow = csv.writer(csvfile).writerow
                for data in all_data:
                    writerow(data[2:3])


        # Generate CSV file with results.
        print(scores)
        csvname = scanpdf[:-9] + '.scores.csv'
        with open(csvname, 'w', newline='') as csvfile:
            writerow = csv.writer(csvfile).writerow
            for name in sorted(scores):
                writerow([name, scores[name]])
        print("Results stored in %s." % csvname)



        # Generate pdf files, with the score and the table of correct answers for each test.
        pdfnames = []
        filename = search_by_extension(directory, '.ptyx')
        for identifier, answers, name, score in all_data:
            output_name = '%s-%s-corr.score' % (filename[:-5], identifier)
            pdfnames.append(output_name)
            print('Generating pdf file for student %s (subject %s, score %s)...'
                                                    % (name, identifier, score))
            latex = generate_answers_and_score(config, name, identifier, score, max_score)
            make_file(output_name, plain_latex=latex,
                                remove=True,
                                formats=['pdf'],
                                quiet=True,
                                )

        output_name = '%s-corr.SCORE' % filename[:-5]
        join_files(output_name, pdfnames, remove_all=True, compress=True)

        # Generate an hidden CSV file for printing or mailing results later.
        csvname = joinpath(directory, '.%s.scan.csv' % basename(scanpdf[:-9]))
        with open(csvname, 'w', newline='') as csvfile:
            writerow = csv.writer(csvfile).writerow
            for (identifier, answers, name, score) in all_data:
                writerow([identifier, name, score])
        print("Config file generated for printing or mailing later.")





#m = lire_image("carres.pbm")
#print(detect_all_squares(m, size=15))
