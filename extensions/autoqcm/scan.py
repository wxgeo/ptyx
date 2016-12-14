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
from os.path import isdir, join as joinpath, expanduser, abspath, dirname
from os import listdir
import subprocess
import tempfile
import argparse
import csv
import sys

from numpy import array, nonzero, transpose
from pylab import imread
from PIL import Image

from parameters import SQUARE_SIZE_IN_CM, CELL_SIZE_IN_CM
# File `compilation.py` is in ../.., so we have to "hack" `sys.path` a bit.
script_path = dirname(abspath(sys._getframe().f_code.co_filename))
sys.path.append(joinpath(script_path, '../..'))
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
        - `error` is the ratio of white pixels allowed is the black square.
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

    def color2debug(from_=None, to_=None, color=(255, 0, 0), display=True, _d={}):
        """Display a red (by default) rectangle for debuging.

        _d is used to store values between two runs, if display=False.
        """
        if not _d.get('rgb'):
            _d['rgb'] = pic.convert('RGB')
        rgb = _d['rgb']
        if from_ is not None:
            if to_ is None:
                to_ = from_
            pix = rgb.load()
            imin, imax = min(from_[0], to_[0]), max(from_[0], to_[0])
            jmin, jmax = min(from_[1], to_[1]), max(from_[1], to_[1])
            for i in range(imin, imax + 1):
                for j in range(jmin, jmax + 1):
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
    n_questions = config['n_questions']
    n_answers = config['n_max_answers']
    students = config['students']
    n_students = len(students)

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
        i1, j1 = find_black_square(m[:maxi,:maxj], size=square_size, error=0.5).__next__()
        minj = int(round((20 - 2*(1 + SQUARE_SIZE_IN_CM))*dpi/2.54))
        i2, j2 = find_black_square(m[:maxi,minj:], size=square_size, error=0.5).__next__()
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
    imax = i1 + 2*square_size
    i3, j3 = find_black_square(m[imin:imax,maxj:minj], size=square_size, error=0.3, mode='c').__next__()
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
            #~ color2debug((i3, j), (i3 + square_size, j), display=False)
            #~ color2debug((i3, j), (i3, j + square_size), display=False)
        #~ else:
            #~ color2debug((i3, j), (i3 + square_size, j), color=(0,0,255), display=False)
            #~ color2debug((i3, j), (i3, j + square_size), color=(0,0,255), display=False)
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

    vpos = max(i1, i2, i3) + 2*square_size

    # ------------------------------------------------------------------
    #                  READ STUDENT NAME (OPTIONAL)
    # ------------------------------------------------------------------
    student_number = None
    student_name = "Unknown student!"
    if n_students:
        search_area = m[vpos:vpos + 4*square_size,:]
        i, j0 = find_black_square(search_area, size=square_size, error=0.3, mode='c').__next__()
        #~ color2debug((vpos + i, j0), (vpos + i + square_size, j0), color=(0,255,0), display=False)
        #~ color2debug((vpos + i, j0), (vpos + i, j0 + square_size), color=(0,255,0))

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
            student_number = n_students - l.index(True) - 1
            student_name = students[student_number]
            print("Student name: %s" % student_name)
    else:
        print("No students list.")

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
    # (So answers will be a matrix, each line corresponding to a question.)
    answers = []
    j = j0
    for kj in range(n_questions):
        answers.append([])
        j = int(round(j0 + (kj + 1)*f_cell_size))
        i = i0
        for ki in range(n_answers):
            i = int(round(i0 + (ki + 1)*f_cell_size))
            answers[-1].append(test_square_color(search_area, i, j, cell_size))

    #~ print("Answers:\n%s" % '\n'.join(str(a) for a in answers))
    print("Result of grid scanning:")
    for question in zip(*answers):
        print(' '.join(('■' if checked else '□') for checked in question))


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
        if ok:
            scores.append(config['correct'])
        elif not proposed:
            scores.append(config['skipped'])
        else:
            scores.append(config['incorrect'])
    print('Scores: ', scores)
    score = sum(scores)

    return identifier, answers, student_name, score




if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Extract information from numerised tests.")
    parser.add_argument('path', help=("Path to a directory which must contain "
                        "a .autoqcm.config file and a .scan.pdf file "
                        "(alternatively, this path may point to any file in this folder)."))
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
        scanpdf = search_by_extension(directory, '.scan.pdf')


        # Read configuration file.
        configfile = search_by_extension(directory, '.autoqcm.config')
        config = read_config(configfile)
        #~ print(config)

        # Extract all images from pdf.
        with tempfile.TemporaryDirectory() as tmp_path:
            #tmp_path = '/home/nicolas/.tmp/scan'
            print(scanpdf, tmp_path)
            print('Extracting all images from pdf, please wait...')
            result = subprocess.run(["pdfimages", "-all", scanpdf, joinpath(tmp_path, 'pic')], stdout=subprocess.PIPE)
            scores = {}
            all_data = []
            for pic in sorted(listdir(tmp_path)):
                print('-------------------------------------------------------')
                #~ print(pic)
                # Extract data from image
                data = scan_picture(joinpath(tmp_path, pic), config)
                all_data.append(data)
                name, score = data[2:]
                if name in scores:
                    raise RuntimeError('2 tests for same student (%s) !' % name)
                scores[name] = score
                print("Score: %s/%s" % (data[3], len(data[1])))


        # Generate CSV file with results.
        print(scores)
        csvname = scanpdf[:-9] + '.scores.csv'
        with open(csvname, 'w', newline='') as csvfile:
            writerow = csv.writer(csvfile).writerow
            for name in sorted(scores):
                writerow([name, scores[name]])



        # Generate pdf files, with the score and the table of correct answers for each test.

        # First, generate the syntax tree once.
        filename = search_by_extension(directory, '.ptyx')
        compiler.read_file(filename)
        compiler.call_extensions()
        compiler.generate_syntax_tree()

        # Since there is only one pass (we generate only the answers, not the blank test),
        # autoqcm_data['answers'] will not be filled automatically at the end of the first pass.
        # So, we have to provide it manually (but fortunately, it has been saved in config).
        compiler.latex_generator.autoqcm_data['answers'] = config['answers']

        # Now, let's generate each pdf.
        pdfnames = []
        for identifier, answers, name, score in all_data:
            output_name = '%s-%s-corr-score' % (filename[:-5], identifier)
            pdfnames.append(output_name)
            make_file(output_name, context={'NUM': identifier,
                                'AUTOQCM__SCORE_FOR_THIS_STUDENT': score,
                                'AUTOQCM__MAX_SCORE': len(answers),
                                'AUTOQCM__STUDENT_NAME': name,
                                'WITH_ANSWERS': True},
                                remove=True,
                                formats=['pdf'],
                                )

        output_name = '%s-corr-score' % filename[:-5]
        join_files(output_name, pdfnames, remove_all=True, compress=True)
        #~ input('-pause-')




        #TODO: if image format is multipage PDF, use `pdfimages -all` to extract images from it.

#m = lire_image("carres.pbm")
#print(detect_all_squares(m, size=15))
