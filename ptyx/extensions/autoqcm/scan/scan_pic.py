from math import degrees, atan, hypot
import builtins
from functools import partial
import io

from PIL import Image
from numpy import array, flipud, fliplr, dot, amin, amax, zeros, int8#, percentile, clip


from .square_detection import test_square_color, find_black_square, \
                             eval_square_color, adjust_checkbox, \
                             color2debug
from ..tools.config_parser import load, real2apparent, apparent2real
from ..parameters import (SQUARE_SIZE_IN_CM, CELL_SIZE_IN_CM,
                        CALIBRATION_SQUARE_POSITION, CALIBRATION_SQUARE_SIZE
                        )

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

class CalibrationError(RuntimeError):
    "Error if calibration failed."
    pass


def round(f, n=None):
    # PEP3141 compatible round() implementation.
    # round(f) should return an integer, but the problem is
    # __builtin__.round(f) doesn't return an int if type(f) is np.float64.
    # See: https://github.com/numpy/numpy/issues/11810
    return (int(builtins.round(f)) if n is None else builtins.round(f, n))


def store_as_WEBP(m):
    output = io.BytesIO()
    im = Image.fromarray((255*m).astype(int8))
    im.save(output, format="WEBP")
    return output

#def uncompress_array(buffer):
#    im = Image.open(buffer)
#    return array(im)/255


def transform(pic, transformation, *args, **kw):
    "Return a transformed version of `pic` and its matrix."
    # cf. http://stackoverflow.com/questions/5252170/specify-image-filling-color-when-rotating-in-python-with-pil-and-setting-expand
    rgba = pic.convert('RGBA')
    rgba = getattr(rgba, transformation)(*args, **kw)
    white = Image.new('RGBA', rgba.size, (255, 255, 255, 255))
    out = Image.composite(rgba, white, rgba)
    pic = out.convert(pic.mode)
    return pic, array(pic)/255.


def find_black_cell(grid, ll, LL, detection_level):
    k = i = j = 0
    for k in range (LL + ll):
        # j < ll <=> k - i < ll <=> k - ll < i <=> i >= k - ll + 1
        for i in range(max(0, k - ll + 1), min(k + 1, LL)):
            j = k - i
#            if grid[i, j] < 100:
#                i0 = half*i   # Add `half` and `m` to the function parameters
#                j0 = half*j   # before running this code.
#                color2debug(m, (i0, j0), (i0 + half, j0 + half))
            if grid[i, j] < detection_level:
                return i, j
    raise LookupError(f"Corner square not found.")


def find_corner_square(m, size, corner, max_whiteness):
    L, l = m.shape
    V, H = corner
    # First, flip the matrix if needed, so that the corner considered
    # is now the top left corner.
    if V == 'b':
        m = flipud(m)
    if H == 'r':
        m = fliplr(m)
    area = m[:L//4,:l//4]
#    color2debug(m, (0, 0), (L//4, l//4), color="blue", display=False)

    # Then, split area into a mesh grid.
    # The mesh size is half the size of the searched square.
    half = size//2
    LL = (L//4)//half
    ll = (l//4)//half
    grid = zeros((LL, ll))

    # For each mesh grid cell, we calculate the whiteness of the cell.
    # (Each pixel value vary from 0 (black) to 1 (white).)
    for i in range(LL):
        for j in range(ll):
            grid[i,j] = area[i*half:(i+1)*half,j*half:(j+1)*half].sum()


    # This is the darkest cell value.
    darkest = grid.min()
    # We could directly collect the coordinates of this cell,
    # which are (grid.argmin()//ll, grid.argmin()%ll).
    # However, the search area is large, and we may detect as the
    # darkest cell one checkbox of the MCQ itself for example,
    # or the ID band.
    # Anyway, even if the core of the black square is not
    # the darkest cell, it should be almost as dark as the darkest.
    detection_level = darkest + 0.15*half**2

    # Then, we will browse the mesh grid, starting from the top left corner,
    # following oblique lines (North-East->South-West), as follows:
    # 1  2  4  7
    # 3  5  8  11
    # 6  9  12 14
    # 10 13 15 16

    # We stop when we found a black cell.
    i, j = find_black_cell(grid, ll, LL, detection_level)

    i0 = half*i
    j0 = half*j

    # Now, we must adjust the position of the square.
    # First, let's adjust it vertically.
    # We have detected the core of the square.
    # The top part of the square (if any) is in the cell just above,
    # and the bottom part (if any) in the cell just below.
    if i == 0:
        i0 = 0
    elif i == LL - 1:
        i0 = half*i
    else:
        # t1 is the percentage of black pixels in the cell above, and t2
        # the percentage in the cell below.
        # We now have a good approximation of the percentage of the square
        # to be found in the upper cell and in the lower cell.
        # So, t2/(t1 + t2)*half is approximatively the vertical position
        # of the square, starting from the top of the upper cell.
        t1 = grid[i - 1, j]
        t2 = grid[i + 1, j]
        if t1 + t2 == 0:
            raise NotImplementedError
        i0 = round((i - 1 + t2/(t1 + t2))*half)

    # Same procedure, but horizontally now.
    if j == 0:
        j0 = 0
    elif j == ll - 1:
        j0 = half*j
    else:
        t1 = grid[i, j - 1]
        t2 = grid[i, j + 1]
        if t1 + t2 == 0:
            raise NotImplementedError
        j0 = round((j - 1 + t2/(t1 + t2))*half)

    # Adjust line by line for more precision.
    # First, vertically.
    j1 = j0
    j2 = j0 + size
    shift_down = False
    while i0 < L//4 - size and area[i0+size,j1:j2].sum() < area[i0,j1:j2].sum():
        # shift one pixel down
        i0 += 1
        shift_down = True
    if not shift_down:
        while i0 > 0 and area[i0-1,j1:j2].sum() < area[i0+size-1,j1:j2].sum():
            # shift one pixel up
            i0 -= 1

    # Then, adjust horizontally.
    i1 = i0
    i2 = i0 + size
    shift_right = False
    while j0 < l//4 - size and area[i1:i2,j0+size].sum() < area[i1:i2,j0].sum():
        # shift one pixel right
        j0 += 1
        shift_right = True
    if not shift_right:
        while j0 > 0 and area[i1:i2,j0-1].sum() < area[i1:i2,j0+size-1].sum():
            # shift one pixel left
            j0 -= 1

    # Test the result. If the square is too dim, raise LookupError.
    whiteness_measure = m[i0:i0+size,j0:j0+size].sum()/size**2
    print(f'Corner square {corner} found...')
#    color2debug(m, (i0, j0), (i0 + size, j0 + size))
    if whiteness_measure > max_whiteness:
        print(f'WARNING: Corner square {corner} not found '
              f'(not dark enough: {whiteness_measure}!)')
        color2debug(m, (i0, j0), (i0 + size, j0 + size), color='blue', display=False)
        raise LookupError(f"Corner square {corner} not found.")

    if V == 'b':
        i0 = L - 1 - i0 - size
    if H == 'r':
        j0 = l - 1 - j0 - size

    return i0, j0


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
#    h = w = round(2*(1 + SQUARE_SIZE_IN_CM)*cm)
    max_whiteness = 0.55
    # Make a mutable copy of frozenset CORNERS.
    corners = set(CORNERS)
    positions = {}
    for corner in CORNERS:
        try:
            i, j = find_corner_square(m, square_size, corner, max_whiteness)
        # ~ # We may have only detected a part of the square by restricting
        # ~ # the search area, so extend search by the size of the square.
        # ~ i, j = find_corner_square(m, square_size, corner, h + square_size,
                                  # ~ w + square_size, tolerance, whiteness)
            color2debug(m, (i, j), (i + square_size,
                                    j + square_size), display=False)
            positions[corner] = i, j
            corners.remove(corner)
        except LookupError:
            pass

        # ~ if input(len(positions)) == 'd':
            # ~ color2debug(m)

    # If one calibration square is missing (a corner of the sheet is
    # folded for example), it will be generated from the others.

#    color2debug(m)
    if len(positions) <= 2:
        color2debug(m)
        raise CalibrationError('Only 2 squares found, calibration failed !')

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
            print(f'Removing {CORNER_NAMES[lighter_corner]} corner '
                  f'(too light: {darkness[lighter_corner]} !)')
            del positions[lighter_corner]

    if len(positions) == 4:
        if n <= 2:
            for (i, j) in positions.values():
                color2debug(m, (i, j), (i + square_size, j + square_size),
                            display=False)
            color2debug(m)
            print('n =', n)
            raise CalibrationError("Something wrong with the corners !")


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
            color2debug(m, (i, j), (i + CALIBRATION_SQUARE_SIZE,
                        j + CALIBRATION_SQUARE_SIZE), color="cyan", display=False)

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
                            error=0.3, gray_level=.5, mode='column', debug=False).__next__()
    i3 += i1
    j3 += j1
    color2debug(m, (i3, j3), (i3 + square_size, j3 + square_size), display=False)
    return i3, j3



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
    calib_square = round(CALIBRATION_SQUARE_SIZE*cm)
    calib_shift_mm = 10*(2*CALIBRATION_SQUARE_POSITION + CALIBRATION_SQUARE_SIZE)

    # Detect the four big squares at the top left, top right, bottom left
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
    positions, *_ = detect_four_squares(m, calib_square, cm,
                                        max_alignment_error_cm=2, debug=debug)
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

    # XXX: implement other paper sheet sizes. Currently only A4 is supported.

    # Distance between the top left corners of the left and right squares is:
    # 21 cm - (margin left + margin right + 1 square width)
    h_pixels_per_mm = (j2 - j1)/(210 - calib_shift_mm)
    # Distance between the top left corners of the top and bottom squares is:
    # 29.7 cm - (margin top + margin bottom + 1 square height)
    v_pixels_per_mm = (i2 - i1)/(297 - calib_shift_mm)
    cm = 10*(h_pixels_per_mm + 1.5*v_pixels_per_mm)/2.5
    print(f"Detect pixels/cm: {cm}")

    # Redetect calibration squares.
    positions, (i1, j1), (i2, j2) = detect_four_squares(m, calib_square, cm,
                                                        debug=debug)


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
            i = L - 1 - i - calib_square
            j = l - 1 - j - calib_square
            V, H = corner
            p[corner] = i, j
            color2debug(m, (i, j), (i + calib_square, j + calib_square),
                        color='green', display=False)
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
            raise CalibrationError("Can't find identification band !")


    # Distance between the top left corners of the left and right squares is:
    # 21 cm - (margin left + margin right + 1 square width)
    h_pixels_per_mm = (j2 - j1)/(210 - calib_shift_mm)
    # Distance between the top left corners of the top and bottom squares is:
    # 29.7 cm - (margin top + margin bottom + 1 square height)
    v_pixels_per_mm = (i2 - i1)/(297 - calib_shift_mm)
#    cm = 10*(h_pixels_per_mm + 1.5*v_pixels_per_mm)/2.5



    print(positions)
    for c, (i, j) in positions.items():
        color2debug(m, (i, j), (i + CALIBRATION_SQUARE_SIZE,
                                j + CALIBRATION_SQUARE_SIZE), display=False)
    color2debug(m, (i3, j3), (i3 + square_size, j3 + square_size), display=False)
    if debug:
        color2debug(m)
    else:
        color2debug()
    # ~ input('- pause -')

    return m, h_pixels_per_mm, v_pixels_per_mm, positions['tl'], (i3, j3)


def edit_answers(m, boxes, answered, config, test_ID, xy2ij, cell_size):
    print('Please verify answers detection:')
    input('-- Press ENTER --')
    process = color2debug(m, wait=False)
    while True:
        ans = input('Is this correct ? [(y)es/(N)o]')
        if ans.lower() in ('y', 'yes'):
            process.terminate()
            process.terminate()
            return answered

        while True:
            ans = input('Write a question number, or 0 to escape:')
            if ans == '0':
                break
            try:
                q0 = int(ans)
            except ValueError:
                continue
            q = apparent2real(q0, None, config, test_ID)
            if q not in answered:
                print('Invalid question number.')
                continue

            ans = input('Add or remove answers (Example: +2 -1 -4 to add answer 2, '
                        'and remove answers 1 et 4):')
            checked = answered[q]
            try:
                for val in ans.split():
                    op, a0 = val[0], int(val[1:])
                    q, a = apparent2real(q0, a0, config, test_ID)
                    if op == '+':
                        if a in checked:
                            print(f'Warning: {a0} already in answers.')
                        else:
                            checked.add(a)
                    elif op == '-':
                        if a in checked:
                            checked.remove(a)
                        else:
                            print(f'Warning: {a0} not in answers.')
                    else:
                        print(f'Invalid operation: {val!r}')
            except ValueError:
                print('Invalid answer number.')
                continue
            answered[q] = checked
            process.terminate()
            # Color answers
            valid_answers = {}
            for key, pos in boxes.items():
                # ~ should_have_answered = set() # for debuging only.
                i, j = xy2ij(*pos)
                i, j = adjust_checkbox(m, i, j, cell_size)
                q, a = key[1:].split('-')
                # `q` and `a` are real questions and answers numbers, that is,
                # questions and answers numbers before shuffling.
                q = int(q)
                a = int(a)
                valid_answers.setdefault(q, set()).add(a)
                if a in answered[q]:
                    color2debug(m, (i, j), (i + cell_size, j + cell_size),
                                thickness=5, color='green', display=False)

            for q in answered:
                if answered[q] - valid_answers[q]:
                    answered[q] &= valid_answers[q]
                    print('Warning: invalid answers numbers were dropped.')
            process = color2debug(m, wait=False)




def scan_picture(filename, config, manual_verification=None,
                 already_verified=frozenset(), debug=False):
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
    # Increase contrast if needed (the lightest pixel must be white,
    # the darkest must be black).
    min_val = amin(m)
    max_val = amax(m)
    if debug:
        color2debug(m, display=True)
        print(f'Old range: {min_val} - {max_val}')
    if min_val > 0 or max_val < 255 and max_val - min_val > 0.2:
        m = (m - min_val)/(max_val - min_val)
        if debug:
            print(f'New range: {amin(m)} - {amax(m)}')
            color2debug(m, display=True)
    else:
        print(f'Warning: not enough contrast in picture {filename!r} !')

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
    half_cell = round(f_cell_size/2)

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

    test_ID = 0
    # Test the color of the 15 following squares,
    # and interpret it as a binary number.

    for k in range(24):
        j_ = round(j + (k + 1)*f_square_size)
        if k%2:
            color2debug(m, (i, j_), (i + square_size, j_ + square_size), display=False)
        else:
            color2debug(m, (i, j_), (i + square_size, j_ + square_size), color=(0,0,255), display=False)
        if test_square_color(m, i, j_, square_size, proportion=0.5, gray_level=0.5):
            test_ID += 2**k
            #~ print((k, (i3, j)), " -> black")
        #~ else:
            #~ print((k, (i3, j)), " -> white")

    # ~ color2debug(m)
    # Nota: If necessary (although this is highly unlikely !), one may extend protocol
    # by adding a second band (or more !), starting with a black square.
    # This function will test if a black square is present below the first one ;
    # if so, the second band will be joined with the first
    # (allowing 2**30 = 1073741824 different values), and so on.

    page = test_ID%256
    print("Page read: %s" % page)
    test_ID = test_ID//256
    print("Test ID read: %s" % test_ID)



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
            i, j0 = find_black_square(search_area, size=square_size, error=0.3, mode='column').__next__()
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
            ID_length, max_digits, digits = config['id_format']
            # ~ height = ID_length*cell_size

            i0, j0 = xy2ij(*config['id-table-pos'])

#            color2debug(m, (i0, j0), (i0 + cell_size, j0 + cell_size), color=(0,255,0))

            # Scan grid row by row. For each row, the darker cell is retrieved,
            # and the associated caracter is appended to the ID.
            all_ID_are_of_the_same_length = (len(set(len(ID) for ID in ids)) == 1)

            ev = eval_square_color
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
                        # To test the blackness, we exclude the top left corner,
                        # which contain the cell number and may alter the result.
                        # So, we divide the cell in four squares, and calculate
                        # the mean blackness of the bottom left, bottom right
                        # and top right squares (avoiding the top left one).
                        blackness = (ev(m, i, j + half_cell, half_cell) +
                                     ev(m, i + half_cell, j, half_cell) +
                                     ev(m, i + half_cell, j + half_cell, half_cell)
                                     )/3
                        # ~ color2debug(m, (i, j + half_cell), (i + half_cell, j + 2*half_cell), display=True)
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
                print(f"ID list: {ids!r}")
                print(f"Warning: invalid student id {student_ID!r} !")
                # ~ color2debug(m)


        else:
            print("No students list.")

        print("Student name:", student_name)




    # ------------------------------------------------------------------
    #                      READ ANSWERS
    # ------------------------------------------------------------------

    answered = {}
    positions = {}
    displayed_questions_numbers = {}
    output = {'ID': test_ID, 'page': page, 'name': student_name, 'file': filename,
            'answered': answered, 'positions': positions, 'matrix': m,
            'cell_size': cell_size, 'questions_nums': displayed_questions_numbers,
            'verified': None}

    try:
        boxes = config['boxes'][test_ID][page]
    except KeyError:
        print(f'WARNING: ID {test_ID!r} - page {page!r} not found in config file !\n'
              f'Maybe ID {test_ID!r} - page {page!r} is an empty page ?')
        return output

    ordering = config['ordering'][test_ID]
    mode = config['mode']
    correct_answers = config['correct_answers']

    # Detect the answers.
    print('\n=== Reading answers ===')
    print(f"Mode: *{mode['default']}* correct answers must be checked.")
    print('Rating:')
    print(f"• {config['correct']['default']} for correctly answered question,")
    print(f"• {config['incorrect']['default']} for wrongly answered question,")
    print(f"• {config['skipped']['default']} for unanswered question.")
    print("Scanning...\n")

    # Using the config file to obtain correct answers list allows some easy customization
    # after the test was generated (this is useful if some tests questions were flawed).

    # Store blackness of checkboxes, to help detect false positives
    # and false negatives.
    blackness = {}
    core_blackness = {}

    for key, pos in boxes.items():
        # ~ should_have_answered = set() # for debuging only.
        i, j = xy2ij(*pos)
        i, j = adjust_checkbox(m, i, j, cell_size)
        q, a = key[1:].split('-')
        # `q` and `a` are real questions and answers numbers, that is,
        # questions and answers numbers before shuffling.
        q = int(q)
        a = int(a)
        # `q0` and `a0` keep track of apparent question and answers numbers,
        # which will be used on output to make debuging easier.
        q0, a0 = real2apparent(q, a, config, test_ID)
        displayed_questions_numbers[q] = q0

#        answer_is_correct = (a in correct_answers)

        test_square = partial(test_square_color, m, i, j, cell_size, margin=5)
        color_square = partial(color2debug, m, (i, j),
                               (i + cell_size, j + cell_size), display=False)

        if q not in answered:
            answered[q] = set()
            print(f'\n{ANSI_CYAN}• Question {q0}{ANSI_RESET} (Q{q})')

        # The following will be used to detect false positives or false negatives later.
        blackness[(q, a)] = eval_square_color(m, i, j, cell_size, margin=4)
        core_blackness[(q, a)] = eval_square_color(m, i, j, cell_size, margin=7)
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
    ceil = 1.5*sum(blackness.values())/len(blackness) + 0.02
    core_ceil = 1.2*sum(core_blackness.values())/len(core_blackness) + 0.01
    for (q, a) in blackness:
        if a not in answered[q] and (blackness[(q, a)] > ceil
                                  or core_blackness[(q, a)] > core_ceil):
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
    core_floor = max(.2*max(core_blackness.values()), max(core_blackness.values()) - 0.3)
    for (q, a) in blackness:
        if a in answered[q] and (blackness[(q, a)] < floor
                                or core_blackness[(q, a)] < core_floor):
            print('False positive detected', (q, a))
            # This is probably a false positive, but we'd better verify manually.
            manual_verification = (manual_verification is not False)
            answered[q].discard(a)
            # Change box color for manual verification.
            i, j = positions[(q, a)]
            color2debug(m, (i, j), (i + cell_size, j + cell_size), color='magenta', thickness=5, display=False)


    # ~ color2debug(m, (0,0), (0,0), display=True)
    # ~ print(f'\nScore: {ANSI_REVERSE}{score:g}{ANSI_RESET}\n')
    if manual_verification is True and (test_ID, page) not in already_verified:
        print(already_verified)
        print(test_ID, page)
        answered = edit_answers(m, boxes, answered, config, test_ID, xy2ij, cell_size)
    elif debug:
        color2debug(m)
    else:
        color2debug()

    output['verified'] = manual_verification
    return output

