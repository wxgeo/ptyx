#!/usr/bin/env python3

# --------------------------------------
#                  Scan
#     Extract info from numerised tests
# --------------------------------------
#    PTYX
#    Python LaTeX preprocessor
#    Copyright (C) 2009-2020  Nicolas Pourcelot
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


from os.path import (isdir, isfile, join, expanduser, abspath,
                     dirname, basename)
from os import listdir, mkdir
import tempfile
from shutil import rmtree
import subprocess
import csv
import sys
import pickle

## File `compilation.py` is in ../.., so we have to "hack" `sys.path` a bit.
#script_path = dirname(abspath(sys._getframe().f_code.co_filename))
#sys.path.insert(0, join(script_path, '../..'))

from ..compile.header import answers_and_score
from ..tools.config_parser import load
from .scan_pic import (scan_picture, ANSI_YELLOW, ANSI_RESET, ANSI_CYAN,
                      ANSI_GREEN, ANSI_RED, color2debug, CalibrationError,
                      store_as_WEBP, load_as_matrix)
from .amend import amend_all
from .pdftools import extract_pictures_from_pdf, PIC_EXTS
from .args import parser


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
    return join(directory, names[0])


def print_framed_msg(msg):
    decoration = max(len(line) for line in msg.split('\n'))*'-'
    print(decoration)
    print(msg)
    print(decoration)
    



def read_name_manually(matrix_or_path, ID, config, more_infos, default=None):
    if isinstance(matrix_or_path, str):
        matrix = load_as_matrix(matrix_or_path)
    else:
        matrix = matrix_or_path
    student_ids = config['ids']
    student_ID = ''
    print('Name can not be read automatically.')
    print('Please read the name on the picture which will be displayed now.')
    input('-- Press enter --')
#    subprocess.run(["display", "-resize", "1920x1080", pic_path])
    #TODO: use first letters of students name to find student.
    #(ask again if not found, or if several names match first letters)
    process = None
    while True:
        L, l = matrix.shape
        # Don't relaunch process if it is still alive.
        # (process.poll() is not None for dead processes.)
        if process is None or process.poll() is not None:
            process = color2debug(matrix[0:int(3/4*l),:], wait=False)
        name = input('Student name or ID:').strip()
        if not name:
            if default is None:
                continue
            name = default
        if student_ids:
            if name in student_ids:
                name, student_ID = student_ids[name], name
            elif any((d in name) for d in '0123456789'):
                # This is not a student name !
                print('Unknown ID.')
                continue
        print("Name: %s" % name)
        if input("Is it correct ? (Y/n)").lower() not in ("y", "yes", ""):
            continue
        if name:
            break
    process.terminate()
    more_infos[ID] = (name, student_ID)
    return name, student_ID



def test_integrity(config, data):
    """For every test:
    - all pages must have been scanned,
    - all questions must have been seen."""
    questions_not_seen = {}
    pages_not_seen = {}
    for ID in data:
        questions = set(config['ordering'][ID]['questions'])
        diff = questions - set(data[ID]['answered'])
        if diff:
            questions_not_seen[ID] = ', '.join(str(q) for q in diff)
        # All tests may not have the same number of pages, since
        # page breaking will occur at a different place for each test.
        pages = set(config['boxes'][ID])
        diff = pages - set(data[ID]['pages'])
        if diff:
            pages_not_seen[ID] = ', '.join(str(p) for p in diff)
    if pages_not_seen:
        print('= WARNING =')
        print('Pages not seen:')
        for ID in sorted(pages_not_seen):
            print(f'    • Test {ID}: page(s) {pages_not_seen[ID]}')
    if questions_not_seen:
        print('=== ERROR ===')
        print('Questions not seen !')
        for ID in sorted(questions_not_seen):
            print(f'    • Test {ID}: question(s) {questions_not_seen[ID]}')

    if questions_not_seen:
        # Don't raise an error for pages not found (only a warning in log)
        # if all questions were found, this was probably empty pages.
        raise RuntimeError(f"Questions not seen ! (Look at message above).")


def keep_previous_version(ID, p, already_seen, data, pic_path):
    """Test if a previous version of the same page exist.
    
    If so, it probably means the page has been scanned twice, but it could
    also indicate a more serious problem (for example, tests with the same ID
    have been given to different students !). 
    As a precaution, we should signal the problem to the user, and ask him
    what he wants to do.
    """
    if (ID, p) not in already_seen:
        # Everything OK.
        already_seen.add((ID, p))
        return False
    # We have a problem: this is is a duplicate.
    # In other words, we have 2 different versions of the same page.
    # Ask the user what to do. 
    print(f'Error: Page {p} of test #{ID} seen twice '
                f'(in "{data[ID]["pic"]}" and "{pic_path}") !')
    while True:
        print('What must we do ?')
        print('- See pictures (s)')
        print('- Keep only first one (f)')
        print('- Keep only last one (l)')
        # ~ print('- Modify this test ID and enter student name (m)')
        # ~ print('  (This will not modify correction)')
        # ~ print('Hint: options f/l are useful if the same page was '
              # ~ 'scanned twice, option m if the same test was given '
              # ~ 'to 2 different students.')

        ans = input('Answer:')
        if ans in ('l', 'f'):
            # if ans == 'l', do nothing.
            # (By default, last version will overwrite first one).
            return (ans == 'f')
        # ~ elif ans == 'm':
            # ~ ID = input('Enter some digits as new test ID:')
            # ~ ans = input(f'New ID: {ID!r}. Is it correct (Y/n) ?')
            # ~ if not ans.isdecimal():
                # ~ print('ID must only contain digits.')
            # ~ elif ans.lower() in ("y", "yes", ""):
                # ~ pic_data['name'] = ''
                # ~ # Have a negative ID to avoid conflict with existing ID.
                # ~ pic_data['ID'] = -int(ID)
                # ~ break
        elif ans == 's':
            with tempfile.TemporaryDirectory() as tmpdirname:
                path = join(tmpdirname, 'test.png')
                # https://stackoverflow.com/questions/39141694/how-to-display-multiple-images-in-unix-command-line
                subprocess.run(["convert", data[ID]["pic"], pic_path, "-append", path])
                subprocess.run(["feh", "-F", path])
                input('-- pause --')


def pic_names_iterator(data):
    for d in data.values():
        for pic_data in d['pages'].values():
            yield basename(pic_data['pic_path'])


def extract_name(ID, d, data, pic_path, pic_data, CFG_PATH, args, matrix, config, more_infos, name2sheetID):
    # (a) The first page should contain the name
    #     ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾
    # However, if the name was already set (using `more_infos`),
    # don't overwrite it.
    if not d['name']:
        # Store the name read (except if ask not to do so).
        if not args.ask_for_name:
            d['name'] = pic_data['name']

    name = d['name']

    # (b) Update name manually if it was not found
    #     ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾

    if not name:
        name, student_ID = read_name_manually(matrix, ID, config, more_infos)
        # Keep track of manually entered information (will be useful
        # if `scan.py` has to be run again later !)
        with open(CFG_PATH, 'a', newline='') as csvfile:
            writerow = csv.writer(csvfile).writerow
            writerow([str(ID), name])



    # (c) A name must not appear twice
    #     ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾

    while name in name2sheetID:
        print(f"Test #{name2sheetID[name]}: {name}")
        print(f'Test #{ID}: {name}')
        print_framed_msg(f'Error : 2 tests for same student ({name}) !\n'
              "Please modify at least one name (enter nothing to keep a name).")
        # Remove twin name from name2sheetID, and get the corresponding previous test ID.
        ID0 = name2sheetID.pop(name)
        # Ask for a new name.
        name0, student_ID0 = read_name_manually(data[ID0]['pages'][1]['pic_path'], ID, config, more_infos, default=name)
        # Update all infos.
        name2sheetID[name0] = ID0
        data[ID0]['name'] = name0
        data[ID0]['student ID'] = student_ID0
        # Ask for a new name for new test too.
        name, student_ID = read_name_manually(pic_path, ID, config, more_infos, default=name)

    assert name, 'Name should not be left empty at this stage !'
    name2sheetID[name] = ID
    d['name'] = name



def calculate_scores(data, config):
    default_mode = config['mode']['default']
    default_correct = config['correct']['default']
    default_incorrect = config['incorrect']['default']
    default_skipped = config['skipped']['default']

    # Maximal score = (number of questions)x(score when answer is correct)
    MAX_SCORE = 0
    for q in config['correct_answers']:
        if config['mode'].get(q, default_mode) != 'skip':
            MAX_SCORE += int(config['correct'].get(q, default_correct))
    config['max_score'] = MAX_SCORE

    for ID in data:
        print(f'Test {ID} - {data[ID]["name"]}')
        d = data[ID]
        for q in sorted(d['answered']):
            answered = set(d['answered'][q])
            correct_ones = set(config['correct_answers'][q])
            mode = config['mode'].get(q, default_mode)

            if mode == 'all':
                ok = (answered == correct_ones)
            elif mode == 'some':
                # Answer is valid if and only if :
                # (proposed ≠ ∅ and proposed ⊆ correct) or (proposed = correct = ∅)
                ok = ((answered and answered.issubset(correct_ones))
                       or (not answered and not correct_ones))
            elif mode == 'skip':
                print(f'Question {q} skipped...')
                continue
            else:
                raise RuntimeError('Invalid mode (%s) !' % mode)
            if ok:
                earn = float(config['correct'].get(q, default_correct))
                color = ANSI_GREEN
            elif not answered:
                earn = float(config['skipped'].get(q, default_skipped))
                color = ANSI_YELLOW
            else:
                earn = float(config['incorrect'].get(q, default_incorrect))
                color = ANSI_RED
            print(f'-  {color}Rating (Q{q}): {color}{earn:g}{ANSI_RESET}')
            d['score'] += earn
            d['score_per_question'][q] = earn
            
    return MAX_SCORE






########################################################################
#                                                                      #
#                                                                      #
#                             MAIN PROCEDURE                           #
#                                                                      #
#                                                                      #
########################################################################


def scan(parser=parser):
    """Main procedure : mark the examination papers.

    Usually, one will call script `bin/scan` from command line,
    which itself calls `scan()` (this procedure).
    `parser` must be the `ArgumentParser` instance defined in the same file,
    but may be tuned for testing before passing it to `scan()`.
    """
    args = parser.parse_args()
    DIR = abspath(expanduser(args.path))
    if not isdir(DIR):
        DIR = dirname(DIR)
        if not isdir(DIR):
            raise FileNotFoundError('%s does not seem to be a directory !' % DIR)

    if args.picture:
        # f1-pic-003.jpg (page 25)
        # f12-pic-005.jpg
        # f12-pic-003.jpg
        # f12-pic-004.jpg
        # f12-pic-013.jpg
        # f7-pic-013.jpg
        # f9-pic-004.jpg
        # f9-pic-005.jpg
        # f13-pic-002.jpg
        if not any(args.picture.endswith(ext) for ext in PIC_EXTS):
            raise TypeError('Allowed picture extensions: ' + ', '.join(PIC_EXTS))
        # This is used for debuging (it allows to test pages one by one).
        configfile = search_by_extension(DIR, '.autoqcm.config.json')
        config = load(configfile)
        # ~ print(config)
        pic_path = abspath(expanduser(args.picture))
        if not isfile(pic_path):
            pic_path = join(DIR, '.scan', 'pic', args.picture)
        verify = (args.manual_verification is not False)
        pic_data, _ = scan_picture(pic_path, config, manual_verification=verify)
        print(pic_data)
        sys.exit(0)

    # This is the usual case: tests are stored in only one big pdf file ;
    # we will process all these pdf pages.


    # ------------------
    # Generate the paths
    # ------------------

    INPUT_DIR = args.scan or join(DIR, 'scan')

    # `.scan` directory is used to write intermediate files.
    # Directory tree:
    # .scan/
    # .scan/pic -> pictures extracted from the pdf
    # .scan/cfg/more_infos.csv -> missing students names.
    # .scan/cfg/verified.csv -> pages already verified.
    # .scan/cfg/skipped.csv -> pages to skip.
    # .scan/scores.csv
    # .scan/.tmp_datafile
    SCAN_DIR = join(args.dir or DIR, '.scan')
    CFG_DIR = join(SCAN_DIR, 'cfg')
    PIC_DIR = join(SCAN_DIR, 'pic')
    PDF_DIR = join(SCAN_DIR, 'pdf')

    if args.reset and isdir(SCAN_DIR):
        rmtree(SCAN_DIR)

    for directory in (SCAN_DIR, CFG_DIR, PIC_DIR, PDF_DIR):
        print(directory)
        if not isdir(directory):
            mkdir(directory)

    base_name = basename(search_by_extension(DIR, '.ptyx'))[:-5]
    SCORES_PDF_PATH = join(PDF_DIR, '%s-scores' % base_name)



    # Read configuration file.
    configfile = search_by_extension(DIR, '.autoqcm.config.json')
    config = load(configfile)

    # Extract images from all the PDF files of the input directory.
    extract_pictures_from_pdf(INPUT_DIR, PIC_DIR)

    # Read manually entered informations (if any).
    more_infos = {} # sheet_id: (name, student_id)
    CFG_PATH = join(CFG_DIR, 'more_infos.csv')
    if isfile(CFG_PATH):
        with open(CFG_PATH, 'r', newline='') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                try:            
                    sheet_ID, name, student_ID = row
                except ValueError:
                    sheet_ID, name = row
                    student_ID = ''
                more_infos[int(sheet_ID)] = (name, student_ID)
            print("Retrieved infos:", more_infos)

    # List manually verified pages.
    # They should not be verified anymore.
    verified = set()
    VERIF_PATH = join(CFG_DIR, 'verified.csv')
    if isfile(VERIF_PATH):
        with open(VERIF_PATH, 'r', newline='') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                sheet_id, page = row
                verified.add((int(sheet_id), int(page)))
            print("Pages manually verified:", verified)

    PICKLE_PATH = join(SCAN_DIR, '.tmp_datafile')
    if isfile(PICKLE_PATH):
        with open(PICKLE_PATH, 'rb') as f:
            data = pickle.load(f)
    else:
        data = {}
    # Dict `data` will collect data from all scanned tests.
    #...............................................................
    # FORMAT: {ID: {'pages': (dict) the pages seen, and all related informations,
    #               'answers': ({int: set}) the answers of the student for each question,
    #               'score': (float) the test score,
    #               'name': (str) the student name,
    #               'last_pic': (str) last image seen full path,
    #               },
    #           ...
    #          }
    #...............................................................
    # 
    
    skipped = set(pic_names_iterator(data))    
    
    # List skipped pictures.
    # Next time, they will be skipped with no warning.
    SKIP_PATH = join(CFG_DIR, 'skipped.csv')
    if isfile(SKIP_PATH):
        with open(SKIP_PATH, 'r', newline='') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                picture, = row
                skipped.add(picture)
            print("Pictures skipped:", skipped)

    
    # ---------------------------------------
    # Extract informations from the pictures.
    # ---------------------------------------

    name2sheetID = {d['name']: ID for ID, d in data.items()}
    # `name2sheetID` is used to retrieve the data associated with a name.
    # FORMAT: {name: test ID}


    already_seen = set((ID, p) for ID, d in data.items() for p in d['pages'])
    # Set `already_seen` will contain all seen (ID, page) couples.
    # It is used to catch an hypothetic scanning problem:
    # we have to be sure that the same page on the same test is not seen
    # twice.

    pic_list = sorted(f for f in listdir(PIC_DIR)
                    if any(f.lower().endswith(ext) for ext in PIC_EXTS))

    for i, pic in enumerate(pic_list, start=1):
        if not (args.start <= i <= args.end):
            continue
        if pic in skipped:
            continue
        print('-------------------------------------------------------')
        print('Page', i)
        print('File:', pic)

        # 1) Extract all the data of an image
        #    ‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾

        pic_path = join(PIC_DIR, pic)
        try:
            pic_data, matrix = scan_picture(pic_path, config,
                                manual_verification=args.manual_verification,
                                already_verified=verified)
            # `pic_data` FORMAT is specified in `scan_pic.py`.
            # (Search for `pic_data =` in `scan_pic.py`).
            
            # We will store a compressed version of the matrix.
            # (It would consume too much memory else).
            pic_data['webp'] = store_as_WEBP(matrix)
        except CalibrationError:
            print(f'WARNING: {pic_path} seems invalid ! Skipping...')
            input('-- PAUSE --')
            with open(SKIP_PATH, 'a', newline='') as csvfile:
                writerow = csv.writer(csvfile).writerow
                writerow([pic])
            continue

        if pic_data['verified']:
            # If the page has been manually verified, keep track of it,
            # so it won't be verified next time if a second pass is needed.
            with open(VERIF_PATH, 'a', newline='') as csvfile:
                writerow = csv.writer(csvfile).writerow
                writerow([str(pic_data['ID']), str(pic_data['page'])])

        
        ID = pic_data['ID']
        p = pic_data['page']
        
        if keep_previous_version(ID, p, already_seen, data, pic_path):
            continue
        
        


        # 2) Gather data
        #    ‾‾‾‾‾‾‾‾‾‾‾
        name, student_ID = more_infos.get(ID, ('', ''))
        d = data.setdefault(ID, {'pages': {}, 'score': 0,
                                 'name': name,
                                 'student ID': student_ID,
                                 'answered': {},
                                 'score': 0,
                                 'score_per_question': {}})
        d['pages'][p] = pic_data
        d['last_pic'] = pic_path
#        d['pictures'].add(pic_path)
        for q in pic_data['answered']:
            ans = d['answered'].setdefault(q, set())
            ans |= pic_data['answered'][q]

        # 3) 1st page of the test => retrieve the student name
        #    ‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾
        if p == 1:
            extract_name(ID, d, data, pic_path, pic_data, CFG_PATH, args, matrix, config, more_infos, name2sheetID)
            
        # Store work in progress, so we can resume process if something fails...
        with open(PICKLE_PATH, 'wb') as f:
            pickle.dump(data, f)
        
    # ---------------------------
    # Test integrity
    # ---------------------------
    # For every test:
    # - all pages must have been scanned,
    # - all questions must have been seen.

    test_integrity(config, data)


    # ---------------------------
    # Calculate scores
    # ---------------------------

    # Nota: most of the time, there should be only one correct answer.
    # Anyway, this code intends to deal with cases where there are more
    # than one correct answer too.
    # If mode is set to 'all', student must check *all* correct propositions ;
    # if not, answer will be considered incorrect. But if mode is set to
    # 'some', then student has only to check a subset of correct propositions
    # for his answer to be considered correct.

    MAX_SCORE = calculate_scores(data, config)
    print()

    # ---------------------------------------------------
    # Time to synthetize & store all those informations !
    # ---------------------------------------------------

#    # Names list should be empty now.
#    if passed_names:
#        raise RuntimeError(f'Too many names in {args.names!r} !')


    # Generate CSV file with results.
    scores = {d['name']: d['score'] for d in data.values()}
    #~ print(scores)
    scores_path = join(SCAN_DIR, 'scores.csv')
    print(f'{ANSI_CYAN}SCORES (/{MAX_SCORE:g}):{ANSI_RESET}')
    with open(scores_path, 'w', newline='') as csvfile:
        writerow = csv.writer(csvfile).writerow
        writerow(('Name', 'Score'))
        for name in sorted(scores):
            print(f' - {name}: {scores[name]:g}')
            writerow([name, scores[name]])
    if scores.values():
        mean = round(sum(scores.values())/len(scores.values()), 2)
        print(f'{ANSI_YELLOW}Mean: {mean:g}/{MAX_SCORE:g}{ANSI_RESET}')
    else:
        'No score found !'
    print(f"\nResults stored in {scores_path!r}\n")


    # Generate CSV file with ID and pictures names for all students.
    info_path = join(SCAN_DIR, 'infos.csv')
    info = [(d['name'], d['student ID'], ID, d['score'], [d['pages'][p]['pic_path'] for p in d['pages']])
                                                  for ID, d in data.items()]
    print(f'{ANSI_CYAN}SCORES (/{MAX_SCORE:g}):{ANSI_RESET}')
    with open(info_path, 'w', newline='') as csvfile:
        writerow = csv.writer(csvfile).writerow
        writerow(('Name', 'Student ID', 'Test ID', 'Score', 'Pictures'))
        for name, student_ID, ID, score, paths in sorted(info):
            paths = ', '.join(pth.replace(SCAN_DIR, '', 1) for pth in paths)
            writerow([name, student_ID, f'#{ID}', score, paths])
    print(f"Infos stored in {info_path!r}\n")

    amend_all(data, config, save_dir=PDF_DIR)

    if args.correction:
        from compilation import make_file, join_files
        # Generate pdf files, with the score and the table of correct answers for each test.
        pdf_paths = []
        for ID, d in data.items():
            #~ identifier, answers, name, score, students, ids
            name = d['name']
            score = d['score']
            path = join(PDF_DIR, '%s-%s-corr.score' % (base_name, ID))
            pdf_paths.append(path)
            print('Generating pdf file for student %s (subject %s, score %s)...'
                                                    % (name, ID, score))
            latex = answers_and_score(config, name, ID,
                            (score if not args.hide_scores else None), MAX_SCORE)
            make_file(path, plain_latex=latex,
                                remove=True,
                                formats=['pdf'],
                                quiet=True,
                                )
        join_files(SCORES_PDF_PATH, pdf_paths, remove_all=True, compress=True)






#m = lire_image("carres.pbm")
#print(detect_all_squares(m, size=15))
