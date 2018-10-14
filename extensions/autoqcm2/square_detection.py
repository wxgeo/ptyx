import subprocess
import tempfile
from os.path import join

from numpy import array, nonzero, transpose
from PIL import Image




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
    """
    square = m[i:i+size, j:j+size]
    # Test also the core of the square, since borders may induce false
    # positives.
    core = square[2:-2,2:-2]
    # ~ print(core.sum()/(size - 4)**2)
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
        if subprocess.call(['which', 'feh']) != 0:
            raise RuntimeError('The `feh` command is not found, please '
                        'install it (`sudo apt install feh` on Ubuntu).')
        with tempfile.TemporaryDirectory() as tmpdirname:
            path = join(tmpdirname, 'test.png')
            rgb.save(path)
            subprocess.run(["feh", path])
            input('-- pause --')
        del _d[ID]



