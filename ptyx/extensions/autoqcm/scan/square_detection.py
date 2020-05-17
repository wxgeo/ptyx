import subprocess
import tempfile
from os.path import join

from numpy import array, nonzero, transpose, interp, int8
from PIL import Image

COLORS = {'red':        (255, 0, 0),
          'green':      (0, 255, 0),
          'blue':       (0, 0, 255),
          'yellow':     (255, 255, 0),
          'magenta':    (255, 0, 255),
          'cyan':       (0, 255, 255),
          'white':      (255, 255, 255),
          'black':      (0, 0, 0),
          'orange':     (255, 128, 0),
          'purple':     (128, 128, 0),
          }
# See also: https://pypi.org/project/webcolors/



def top_left_iterator(stop, step=1):
    "Return an iterator for coordinates starting from top-left corner."
    # Pixels are visited starting from top-left corner
    # in the following order:
    # 1  3  8  15
    # 4  2  6  13
    # 9  7  5  11
    # 16 14 12 10
    for n in range(0, stop, step):
        yield (n, n)
        for k in range(n - step, -1, -step):
            yield (k, n)
            yield (n, k)



def total_grayness(m):
    return interp(m, [0,0.2,0.8,1], [0, 0.1, 0.9, 1]).sum()


def find_black_rectangle(matrix, width=50, height=50, error=0.30, gray_level=.4, mode='row', debug=False):
    """Detect a black rectangle of given size (in pixels) in matrix.

    The n*m matrix must contain only floats between 0 (white) and 1 (black).

    Optional parameters:
        - `error` is the ratio of white pixels allowed in the black square.
        - `gray_level` is the level above which a pixel is considered to be white.
           If it is set to 0, only black pixels will be considered black ; if it
           is close to 1 (max value), almost all pixels are considered black
           except white ones (for which value is 1.).
        - `mode` is either:
            * 'row' (picture is scanned row by row, from top to bottom)
            * 'column' (picture is scanned column by column, from left to right)

    Return a generator of (i, j) where i is line number and j is column number,
    indicating black squares top left corner.

    """
    # ~ color2debug(matrix)
    # First, convert grayscale image to black and white.
    if debug:
        print(f'`find_black_rectangle` parameters: width={width}, '
              f'height={height}, error={error}, gray_level={gray_level}')
        color2debug(matrix, display=True)
    m = array(matrix, copy=False) < gray_level
    if debug:
        color2debug(1 - m, display=True)
    # Black pixels are represented by False, white ones by True.
    #pic_height, pic_width = m.shape
    per_line = (1 - error)*width
    per_col = (1 - error)*height
    goal = per_line*height
    to_avoid = []
    # Find a black pixel, starting from top left corner,
    # and scanning line by line (ie. from top to bottom).
    if mode == 'row':
        black_pixels = nonzero(m)
    elif mode == 'column':
        black_pixels = reversed(nonzero(transpose(array(m))))
    else:
        raise RuntimeError("Unknown mode: %s. Mode should be either 'row' or 'column'." % repr(mode))
    if debug:
        print(mode, black_pixels)
    for (i, j) in zip(*black_pixels):
        # Avoid to detect an already found square.
        if debug:
            print("Black pixel found at %s, %s" % (i, j))
        # ~ color2debug(m.astype(float), (i, j), (i + width, j + height), color=(255,0,255))
        if any((li_min <= i <= li_max and co_min <= j <= co_max)
                for (li_min, li_max, co_min, co_max) in to_avoid):
            continue
        assert m[i, j] == 1
        total = m[i:i+height, j:j+width].sum()
        if debug:
            print(f"Total: {total} | Goal: {goal}")
            if total >= goal/5:
                color2debug(matrix, (i, j), (i+height, j+width), display=True)
        # ~ print(f'Black pixels ratio: {total}/{width*height} ; Min: {goal}.')
        # ~ input('- pause -')
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




def find_black_square(matrix, size, error=.4, gray_level=.4, **kw):
    return find_black_rectangle(matrix, width=size, height=size, error=error, gray_level=gray_level, **kw)


def detect_all_squares(matrix, size=50, error=0.30):
    return list(find_black_square(matrix, size=size, error=error))



def test_square_color(m, i, j, size, proportion=0.3, gray_level=.75, margin=0, _debug=False):
    """Return True if square is black, False else.

    (i, j) is top left corner of the square, where i is line number
    and j is column number.
    `proportion` is the minimal proportion of black pixels the square must have
    to be considered black (`gray_level` is the level below which a pixel
    is considered black).
    """
    if size <= 2*margin + 4:
        raise ValueError('Square too small for current margins !')
    square = m[i+margin : i+size-margin, j+margin : j+size-margin] < gray_level
    if _debug:
        print(square, square.sum(), len(square)**2)
        print("proportion of black pixels detected: %s (minimum required was %s)"
                                        % (square.sum()/size**2, proportion))
    # Test also the core of the square, since borders may induce false
    # positives if proportion is kept low (like default value).
    core = square[2:-2, 2:-2]
    return square.sum() > proportion*len(square)**2 and core.sum() > proportion*len(core)**2


def eval_square_color(m, i, j, size, margin=0, _debug=False):
    """Return an indice of blackness, which is a float in range (0, 1).
    The bigger the float returned, the darker the square.

    The indice is useful to compare several squares, and find the blacker one.
    Note that the core of the square is considered the more important part to assert
    blackness.

    (i, j) is top left corner of the square, where i is line number
    and j is column number.
    """
    if size <= 2*margin:
        raise ValueError('Square too small for current margins !')
    # Warning: pixels outside the sheet shouldn't be considered black !
    # Since we're doing a sum, 0 should represent white and 1 black,
    # so as if a part of the square is outside the sheet, it is considered
    # white, not black ! This explain the `1 - m[...]` below.
    square = 1 - m[i+margin : i+size-margin, j+margin : j+size-margin]
    return square.sum()/(size - margin)**2



def adjust_checkbox(m, i, j, size, level1=0.5, level2=0.6, delta=5):
    #return (i, j)
    # Try to adjust top edge of the checkbox
    i0, j0 = i, j
    if m[i:i+size, j:j+1].sum() < level1*size:
        for i in range(i0 - delta, i0 + delta + 1):
            if m[i:i+size, j:j+1].sum() > level2*size:
                break
        else:
            i = i0
    if m[i:i+1, j:j+size].sum() < level1*size:
        for j in range(j0 - delta, j0 + delta + 1):
            if m[i:i+1, j:j+size].sum() > level2*size:
                break
        else:
            j = j0
    return i, j





def find_lonely_square(m, size, error=.4, gray_level=.4):
    """Find all black squares surrounded by a white area.

    - `size` is the length of the edge (in pixels).
    - `error` is the ratio of white pixels allowed in the black square.
    - `gray_level` is the level above which a pixel is considered to be white.
       If it is set to 0, only black pixels will be considered black ; if it
       is close to 1 (max value), almost all pixels are considered black
       except white ones (for which value is 1.).

    Return an iterator.
    """
    s = size
    for i, j in find_black_square(m, s, error, gray_level):
        # Test if all surrounding squares are white.
        # (If not, it could be a false positive, caused by a stain
        # or by some student writing.)
        if not any(test_square_color(m, i_, j_, s, proportion=0.5, gray_level=0.5)
                    for i_, j_ in [(i - s, j - s), (i - s, j), (i - s, j + s),
                                   (i, j - s), (i, j + s),
                                   (i + s, j - s), (i + s, j), (i + s, j + s)]):
            yield (i, j)
    # ~ raise LookupError("No lonely black square in the search area.")



def color2debug(array=None, from_=None, to_=None, color='red',
                display=True, thickness=2, fill=False, _d={}, wait=True):
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
    if array is None:
        _d.clear()
        return
    color = COLORS.get(color, color)
    ID = id(array)
    if ID not in _d:
        # Load image only if not loaded previously.
        # .astype(int8) will make more arrays representable.
        _d[ID] = Image.fromarray((255*array).astype(int8)).convert('RGB')
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

        def set_pix(i, j, color):
            "Set safely pixel color (if `i` or `j` is incorrect, do nothing)."
            if 0 <= i < height and 0 <= j < width:
                pix[j, i] = color

        if fill:
            for i in range(imin, imax + 1):
                for j in range(jmin, jmax + 1):
                    set_pix(i, j, color)
        else:
            # left and right sides of rectangle
            for i in range(imin, imax + 1):
                for j in range(jmin, jmin + thickness):
                    set_pix(i, j, color)
                for j in range(jmax + 1 - thickness, jmax + 1):
                    set_pix(i, j, color)
            # top and bottom sides of rectangle
            for j in range(jmin, jmax + 1):
                for i in range(imin, imin + thickness):
                    set_pix(i, j, color)
                for i in range(imax + 1 - thickness, imax + 1):
                    set_pix(i, j, color)

    if display:
        del _d[ID]
        if subprocess.call(['which', 'feh']) != 0:
            raise RuntimeError('The `feh` command is not found, please '
                        'install it (`sudo apt install feh` on Ubuntu).')
        with tempfile.TemporaryDirectory() as tmpdirname:
            path = join(tmpdirname, 'test.png')
            rgb.save(path)
            if wait:
                process = subprocess.run(["feh", "-F", path])
            else:
                process = subprocess.Popen(["feh", "-F", path],
                                           stdin=subprocess.DEVNULL)
            input('-- pause --\n')
            return process


