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


from pathlib import Path
import tempfile
from shutil import rmtree
import subprocess
import csv
import sys
from ast import literal_eval
from hashlib import blake2b

from PIL import Image
from numpy import int8, array
## File `compilation.py` is in ../.., so we have to "hack" `sys.path` a bit.
#script_path = dirname(abspath(sys._getframe().f_code.co_filename))
#sys.path.insert(0, join(script_path, '../..'))

from ..compile.header import answers_and_score
from ..tools.config_parser import load
from .scan_pic import (scan_picture, ANSI_YELLOW, ANSI_RESET, ANSI_CYAN,
                       ANSI_GREEN, ANSI_RED, color2debug, CalibrationError)
from .amend import amend_all
from .pdftools import extract_pdf_pictures, PIC_EXTS
from .tools import search_by_extension, print_framed_msg



def pic_names_iterator(data: str) -> Path:
    "Iterate over all pics found in data (ie. all the pictures already analysed)."
    for d in data.values():
        for pic_data in d['pages'].values():
            path = Path(pic_data['pic_path'])
            # return pdfhash/picnumber.png
            yield path.relative_to(path.parent.parent)


class MCQPictureParser:
    "Main class for parsing pdf files containing all the scanned MCQ."

    def __init__(self, args):
        self.args = args
        # Main paths.
        self.dirs = {}
        self.files = {}
        # All data extracted from pdf files.
        self.data = {}
        # Additionnal informations entered manually.
        self.more_infos = {} # sheet_id: (name, student_id)
        self.config = {}
        # Manually verified pages.
        self.verified = set()
        # `name2sheetID` is used to retrieve the data associated with a name.
        # FORMAT: {name: test ID}
        self.name2sheetID = {}
        # Set `already_seen` will contain all seen (ID, page) couples.
        # It is used to catch an hypothetic scanning problem:
        # we have to be sure that the same page on the same test is not seen
        # twice.
        self.already_seen = set()
        self.skipped = set()

    def load_data(self):
        if self.dirs['data'].is_dir():
            for filename in self.dirs['data'].glob('*/*.scandata'):
                ID = int(filename.stem)
                with open(filename) as f:
                    try:
                        self.data[ID] = literal_eval(f.read())
                    except ValueError as e:
                        # Temporary patch.
                        # set() is not supported by literal_eval() until Python 3.9
                        # XXX: remove this once Ubuntu 22.04 will be released.
                        if sys.version_info < (3, 9):
                            f.seek(0)
                            s = f.read()
                            assert 'set()' in s
                            self.data[ID] = eval(s)
                        else:
                            print(f"ERROR when reading {filename} :")
                            raise e
                    except Exception:
                        print(f"ERROR when reading {filename} :")
                        raise

    def store_data(self, folder: Path, ID, p, matrix):
        with open(folder / f'{ID}.scandata', 'w') as f:
            f.write(repr(self.data[ID]))
        # We will store a compressed version of the matrix.
        # (It would consume too much memory else).
        webp = folder / f'{ID}-{p}.webp'
        Image.fromarray((255*matrix).astype(int8)).save(str(webp), format="WEBP")

    def get_pic(self, ID, p, as_matrix=False):
        webp = self.dirs['data'] / f'{ID}-{p}.webp'
        im = Image.open(str(webp))
        if as_matrix:
            return array(im.convert("L"))/255
        return im

    def _read_name_manually(self, ID, matrix=None, p=None, default=None):
        if matrix is None:
            matrix = self.get_pic(ID, p, as_matrix=True)
        student_ids = self.config['ids']
        student_ID = ''
        print('Name can not be read automatically.')
        print('Please read the name on the picture which will be displayed now.')
        input('-- Press enter --')
    #    subprocess.run(["display", "-resize", "1920x1080", pic_path])
        #TODO: use first letters of students name to find student.
        #(ask again if not found, or if several names match first letters)
        process = None
        while True:
            l = matrix.shape[1]
            # Don't relaunch process if it is still alive.
            # (process.poll() is not None for dead processes.)
            if process is None or process.poll() is not None:
                process = color2debug(matrix[0:int(3/4*l), :], wait=False)
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
        # Keep track of manually entered information (will be useful
        # if `scan.py` has to be run again later !)
#        self.more_infos[ID] = (name, student_ID)
        with open(self.files['cfg'], 'a', newline='') as csvfile:
            writerow = csv.writer(csvfile).writerow
            writerow([str(ID), name, student_ID])
        return name, student_ID


    def _test_integrity(self):
        """For every test:
        - all pages must have been scanned,
        - all questions must have been seen."""
        questions_not_seen = {}
        pages_not_seen = {}
        for ID in self.data:
            questions = set(self.config['ordering'][ID]['questions'])
            diff = questions - set(self.data[ID]['answered'])
            if diff:
                questions_not_seen[ID] = ', '.join(str(q) for q in diff)
            # All tests may not have the same number of pages, since
            # page breaking will occur at a different place for each test.
            pages = set(self.config['boxes'][ID])
            diff = pages - set(self.data[ID]['pages'])
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


    def _keep_previous_version(self, ID, p, pic_path: str) -> bool:
        """Test if a previous version of the same page exist.

        If so, it probably means the page has been scanned twice, but it could
        also indicate a more serious problem (for example, tests with the same ID
        have been given to different students !).
        As a precaution, we should signal the problem to the user, and ask him
        what he wants to do.
        """
        if (ID, p) not in self.already_seen:
            # Everything OK.
            self.already_seen.add((ID, p))
            return False
        # We have a problem: this is is a duplicate.
        # In other words, we have 2 different versions of the same page.
        # Ask the user what to do.
        print(f'Error: Page {p} of test #{ID} seen twice '
                    f'(in "{self.data[ID]["pages"][p]["pic_path"]}" and "{pic_path}") !')
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
            if ans == 's':
                with tempfile.TemporaryDirectory() as tmpdirname:
                    path = Path(tmpdirname) / 'test.png'
                    # https://stackoverflow.com/questions/39141694/how-to-display-multiple-images-in-unix-command-line
                    subprocess.run(["convert", str(self.data[ID]["pages"][p]["pic_path"]), str(pic_path), "-append", str(path)],
                                   check=True)
                    subprocess.run(["feh", "-F", str(path)], check=True)
                    input('-- pause --')


    def _extract_name(self, ID, d, matrix):
        pic_data = d['pages'][1]
        # (a) The first page should contain the name
        #     ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾
        # However, if the name was already set (using `more_infos`),
        # don't overwrite it.
        if not d['name']:
            # Store the name read (except if ask not to do so).
            if not self.args.ask_for_name:
                d['name'] = pic_data['name']

        name = d['name']

        # (b) Update name manually if it was not found
        #     ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾

        if not name:
            name = self._read_name_manually(ID, matrix)[0]

        # (c) A name must not appear twice
        #     ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾
        while name in self.name2sheetID:
            print(f"Test #{self.name2sheetID[name]}: {name}")
            print(f'Test #{ID}: {name}')
            print_framed_msg(f'Error : 2 tests for same student ({name}) !\n'
                  "Please modify at least one name (enter nothing to keep a name).")
            # Remove twin name from name2sheetID, and get the corresponding previous test ID.
            ID0 = self.name2sheetID.pop(name)
            # Ask for a new name.
            name0, student_ID0 = self._read_name_manually(ID0, p=1, default=name)
            # Update all infos.
            self.name2sheetID[name0] = ID0
            self.data[ID0]['name'] = name0
            self.data[ID0]['student ID'] = student_ID0
            # Ask for a new name for new test too.
            name = self._read_name_manually(ID, matrix, default=name)[0]

        assert name, 'Name should not be left empty at this stage !'
        self.name2sheetID[name] = ID
        d['name'] = name



    def _calculate_scores(self):
        cfg = self.config
        default_mode = cfg['mode']['default']
        default_correct = cfg['correct']['default']
        default_incorrect = cfg['incorrect']['default']
        default_skipped = cfg['skipped']['default']

        max_score = 0
        # Take a random student test, and calculate max score for it.
        # Maximal score = (number of questions)x(score when answer is correct)
        for q in next(iter(cfg["ordering"].values()))["questions"]:
            q = str(q)
            if cfg['mode'].get(q, default_mode) != 'skip':
                max_score += int(cfg['correct'].get(q, default_correct))
        cfg['max_score'] = max_score

        for ID in self.data:
            print(f'Test {ID} - {self.data[ID]["name"]}')
            d = self.data[ID]
            for q in sorted(d['answered']):
                answered = set(d['answered'][q])
                correct_ones = set(cfg['correct_answers'][q])
                mode = cfg['mode'].get(q, default_mode)

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
                    earn = float(cfg['correct'].get(q, default_correct))
                    color = ANSI_GREEN
                elif not answered:
                    earn = float(cfg['skipped'].get(q, default_skipped))
                    color = ANSI_YELLOW
                else:
                    earn = float(cfg['incorrect'].get(q, default_incorrect))
                    color = ANSI_RED
                print(f'-  {color}Rating (Q{q}): {color}{earn:g}{ANSI_RESET}')
                d['score'] += earn
                d['score_per_question'][q] = earn


    def _generate_outcome(self):
        max_score = self.config["max_score"]
        # Generate CSV file with results.
        scores = {d['name']: d['score'] for d in self.data.values()}
        #~ print(scores)
        scores_path = self.dirs['scan'] / 'scores.csv'
        print(f'{ANSI_CYAN}SCORES (/{max_score:g}):{ANSI_RESET}')
        with open(scores_path, 'w', newline='') as csvfile:
            writerow = csv.writer(csvfile).writerow
            writerow(('Name', 'Score'))
            for name in sorted(scores):
                print(f' - {name}: {scores[name]:g}')
                writerow([name, scores[name]])
        if scores.values():
            mean = round(sum(scores.values())/len(scores.values()), 2)
            print(f'{ANSI_YELLOW}Mean: {mean:g}/{max_score:g}{ANSI_RESET}')
        else:
            print('No score found !')
        print(f"\nResults stored in {scores_path!r}\n")


        # Generate CSV file with ID and pictures names for all students.
        info_path = self.dirs['scan'] / 'infos.csv'
        info = [(d['name'], d['student ID'], ID, d['score'],
                 [d['pages'][p]['pic_path'] for p in d['pages']])
                                            for ID, d in self.data.items()]
        print(f'{ANSI_CYAN}SCORES (/{max_score:g}):{ANSI_RESET}')
        with open(info_path, 'w', newline='') as csvfile:
            writerow = csv.writer(csvfile).writerow
            writerow(('Name', 'Student ID', 'Test ID', 'Score', 'Pictures'))
            for name, student_ID, ID, score, paths in sorted(info):
                paths = ', '.join(pth.replace(self.dirs['scan'], '', 1) for pth in paths)
                writerow([name, student_ID, f'#{ID}', score, paths])
        print(f"Infos stored in {info_path!r}\n")

        amend_all(self)

        if self.args.correction:
            from ....compilation import make_file, join_files
            # Generate pdf files, with the score and the table of correct answers for each test.
            pdf_paths = []
            for ID, d in self.data.items():
                #~ identifier, answers, name, score, students, ids
                name = d['name']
                score = d['score']
                path = self.dirs['pdf'] / '%s-%s-corr.score' % (self.files['base'], ID)
                pdf_paths.append(path)
                print('Generating pdf file for student %s (subject %s, score %s)...'
                                                        % (name, ID, score))
                latex = answers_and_score(self.config, name, ID,
                                (score if not self.args.hide_scores else None), max_score)
                make_file(path, plain_latex=latex,
                                    remove=True,
                                    formats=['pdf'],
                                    quiet=True,
                                    )
            join_files(self.dirs['results'], pdf_paths, remove_all=True, compress=True)


    def _generate_paths(self):
        root = Path(self.args.path).expanduser().resolve()
        if not root.is_dir():
            root = root.parent
            if not root.is_dir():
                raise FileNotFoundError('%s does not seem to be a directory !' % root)
        self.dirs['root'] = root

        # Read configuration file.
        configfile = search_by_extension(root, '.autoqcm.config.json')
        self.config = load(configfile)

        # ------------------
        # Generate the paths
        # ------------------

        self.dirs['input'] = self.args.scan or (root / 'scan')

        # `.scan` directory is used to write intermediate files.
        # Directory tree:
        # .scan/
        # .scan/pic -> pictures extracted from the pdf
        # .scan/cfg/more_infos.csv -> missing students names.
        # .scan/cfg/verified.csv -> pages already verified.
        # .scan/cfg/skipped.csv -> pages to skip.
        # .scan/scores.csv
        # .scan/data -> data stored as .scandata files (used to resume interrupted scan).
        self.dirs['scan'] = self.args.dir or (self.dirs['root'] / '.scan')
        self.dirs['data'] = self.dirs['scan'] / 'data'
        self.dirs['cfg'] = self.dirs['scan'] / 'cfg'
        self.dirs['pic'] = self.dirs['scan'] / 'pic'
        self.dirs['pdf'] = self.dirs['scan'] / 'pdf'

        if self.args.reset and self.dirs['scan'].is_dir():
            rmtree(self.dirs['scan'])

        for directory in self.dirs.values():
            if not directory.is_dir():
                directory.mkdir()

        self.files['base'] = search_by_extension(self.dirs['root'], '.ptyx').stem
        self.dirs['results'] = self.dirs['pdf'] / (self.files['base'] + "-results")


#    def _extract_pictures_from_pdf(self):
#        # First, we must test if pdf files have changed.
#        # - calculate hash for each file.
#        # - if nothing has changes, pass.
#        # - if new pdf files are found, extract pictures from them and store their hash.
#        # - if pdf files where modified or removed, regenerate everything.
#        # hashlib.sha512(f.read()).hexdigest()



    def load_all_info(self):
        "Load all informations from files."
        self.load_data()

        # Read manually entered informations (if any).
        self.files['cfg'] = self.dirs['cfg'] / 'more_infos.csv'
        if self.files['cfg'].is_file():
            with open(self.files['cfg'], 'r', newline='') as csvfile:
                reader = csv.reader(csvfile)
                for row in reader:
                    try:
                        sheet_ID, name, student_ID = row
                    except ValueError:
                        sheet_ID, name = row
                        student_ID = ''
                    self.more_infos[int(sheet_ID)] = (name, student_ID)
                print("Retrieved infos:", self.more_infos)

        # List manually verified pages.
        # They should not be verified anymore.
        self.files['verified'] = self.dirs['cfg'] / 'verified.txt'
        if self.files['verified'].is_file():
            with open(self.files['verified'], 'r', encoding="utf8", newline='') as file:
                self.verified = set(path.strip() for path in file.readlines())
                print("Pages manually verified:", self.verified)

        self.skipped = set(pic_names_iterator(self.data))

        # List skipped pictures.
        # Next time, they will be skipped with no warning.
        self.files['skipped'] = self.dirs['cfg'] / 'skipped.txt'
        if self.files['skipped'].is_file():
            with open(self.files['skipped'], 'r', encoding="utf8", newline='') as file:
                self.skipped |= set(path.strip() for path in file.readlines())
                print("Pictures skipped:", self.skipped)


    def parse_picture(self):
        "This is used for debuging (it allows to test pages one by one)."
        args = self.args
        if not any(args.picture.endswith(ext) for ext in PIC_EXTS):
            raise TypeError('Allowed picture extensions: ' + ', '.join(PIC_EXTS))
        pic_path = Path(args.picture).expanduser().resolve()
        if not pic_path.is_file():
            pic_path = self.dirs['pic'] / args.picture
        verify = (args.manual_verification is not False)
        pic_data, _ = scan_picture(pic_path, self.config, manual_verification=verify)
        print(pic_data)
        sys.exit(0)


    def _generate_current_pdf_hashes(self) -> dict:
        """Return the hashes of all the pdf files found in `scan/` directory.
        
        Return: {hash: pdf path}
        """
        hashes = dict()
        for path in self.dirs['input'].glob('*.pdf'):
            with open(path, 'rb') as pdf_file:
                hashes[blake2b(pdf_file.read(), digest_size=20).hexdigest()] = path
        return hashes


    def update_input_data(self):
        "Test if input data has changed, and update it if needed."
        hash2pdf: dict = self._generate_current_pdf_hashes()

        # For each removed pdf files, remove corresponding pictures and data
        for path in self.dirs['pic'].iterdir():
            if path not in hash2pdf:
                rmtree(path)
        for path in self.dirs['data'].iterdir():
            if path not in hash2pdf:
                rmtree(path)

        # For each new pdf files, extract all pictures
        for pdfhash, pdfpath in hash2pdf.items():
            folder = self.dirs["pic"] / pdfhash
            if not folder.is_dir():
                extract_pdf_pictures(pdfpath, folder)


    def run(self):
        args = self.args
        self._generate_paths()

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
            self.parse_picture()

        # This is the usual case: tests are stored in only one big pdf file ;
        # we will process all these pdf pages.

        data = self.data
        # Test if the PDF files of the input directory have changed and 
        # extract the images from the PDF files if needed.
        self.update_input_data()
        # Load data from previous run
        self.load_all_info()

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

        # ---------------------------------------
        # Extract informations from the pictures.
        # ---------------------------------------

        self.name2sheetID = {d['name']: ID for ID, d in data.items()}

        self.already_seen = set((ID, p) for ID, d in data.items() for p in d['pages'])

        pic_list = sorted(f for f in self.dirs['pic'].glob("*/*")
                        if f.suffix.lower() in PIC_EXTS)

        for i, pic_path in enumerate(pic_list, start=1):
            if not (args.start <= i <= args.end):
                continue
            pic = pic_path.relative_to(self.dirs['pic'])
            if pic in self.skipped:
                continue
            print('-------------------------------------------------------')
            print('Page', i)
            print('File:', pic)

            # 1) Extract all the data of an image
            #    ‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾

            try:
                # Warning: args.manual_verification can be None, so the order is important
                # below : False and None -> False (but None and False -> None).
                manual_verification = (pic not in self.verified) and args.manual_verification
                pic_data, matrix = scan_picture(pic_path, self.config,
                                                manual_verification)
                # `pic_data` FORMAT is specified in `scan_pic.py`.
                # (Search for `pic_data =` in `scan_pic.py`).

            except CalibrationError:
                print(f'WARNING: {pic_path} seems invalid ! Skipping...')
                input('-- PAUSE --')
                with open(self.files['skipped'], 'a', newline='', encoding="utf8") as file:
                    file.write(f'{pic}\n')
                continue

            if pic_data['verified']:
                # If the page has been manually verified, keep track of it,
                # so it won't be verified next time if a second pass is needed.
                with open(self.files['verified'], 'a', newline='', encoding="utf8") as file:
                    file.write(f'{pic}\n')

            ID = pic_data['ID']
            page = pic_data['page']

            if self._keep_previous_version(ID, page, str(pic_path)):
                continue

            # 2) Gather data
            #    ‾‾‾‾‾‾‾‾‾‾‾
            name, student_ID = self.more_infos.get(ID, ('', ''))
            data_for_this_ID = data.setdefault(ID, {'pages': {},
                                     'name': name,
                                     'student ID': student_ID,
                                     'answered': {},
                                     'score': 0,
                                     'score_per_question': {}})
            data_for_this_ID['pages'][page] = pic_data

            for q in pic_data['answered']:
                ans = data_for_this_ID['answered'].setdefault(q, set())
                ans |= pic_data['answered'][q]

            # 3) 1st page of the test => retrieve the student name
            #    ‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾
            if page == 1:
                self._extract_name(ID, data_for_this_ID, matrix)

            # Store work in progress, so we can resume process if something fails...
            folder = pic_path.parent
            self.store_data(folder, ID, page, matrix)


        # ---------------------------
        # Test integrity
        # ---------------------------
        # For every test:
        # - all pages must have been scanned,
        # - all questions must have been seen.
        self._test_integrity()

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
        self._calculate_scores()
        print()

        # ---------------------------------------------------
        # Time to synthetize & store all those informations !
        # ---------------------------------------------------
        self._generate_outcome()
