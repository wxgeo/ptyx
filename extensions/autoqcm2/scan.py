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


from os.path import (isdir, isfile, join, expanduser, abspath,
                     dirname, basename)
from os import listdir, mkdir, rename
from shutil import rmtree
import subprocess
import argparse
import csv
import sys

# File `compilation.py` is in ../.., so we have to "hack" `sys.path` a bit.
script_path = dirname(abspath(sys._getframe().f_code.co_filename))
sys.path.insert(0, join(script_path, '../..'))

from header import answers_and_score
from compilation import make_file, join_files
from config_reader import read_config
from scan_pic import scan_picture

from scan_pic import ANSI_YELLOW, ANSI_RESET, ANSI_CYAN


PIC_EXTS = ('.jpg', '.jpeg', '.png')





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



def _extract_pictures(pdf_path, dest, page=None):
    "Extract all pictures from pdf file in given `dest` directory. "
    cmd = ["pdfimages", "-all", pdf_path, join(dest, 'pic')]
    if page is not None:
        p = str(page)
        cmd = cmd[:1] + ['-f', p, '-l', p] + cmd[1:]
    #~ print(cmd)
    subprocess.run(cmd, stdout=subprocess.PIPE)

def _export_pdf_to_jpg(pdf_path, dest, page=None):
    print('Convert PDF to PNG, please wait...')
    cmd = ['gs', '-dNOPAUSE', '-dBATCH', '-sDEVICE=jpeg', '-r200',
           '-sOutputFile=' + join(dest, 'page-%03d.jpg'), pdf_path]
    if page is not None:
        cmd = cmd[:1] + ["-dFirstPage=%s" % page, "-dLastPage=%s" % page] + cmd[1:]
    subprocess.run(cmd, stdout=subprocess.PIPE)


def pdf2pic(*pdf_files, dest, page=None):
    "Clear `dest` folder, then extract of pages of the pdf files inside."
    rmtree(dest)
    mkdir(dest)
    tmp_dir = join(dest, '.tmp')
    for i, pdf in enumerate(pdf_files):
        print(f'Extracting all images from {basename(pdf)!r}, please wait...')
        rmtree(tmp_dir, ignore_errors=True)
        mkdir(tmp_dir)
        _extract_pictures(pdf, tmp_dir, page)
        # PDF may contain special files (OCR...) we can't handle.
        # In that case, we will rasterize pdf.
        pics = listdir(tmp_dir)
        if not all(any(f.endswith(ext) for ext in PIC_EXTS) for f in pics):
            rmtree(tmp_dir)
            mkdir(tmp_dir)
            _export_pdf_to_jpg(pdf, tmp_dir, args.page)
        for pic in pics:
            rename(join(tmp_dir, pic), join(dest, f'f{i}-{pic}'))
    rmtree(tmp_dir)



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


def read_name_manually(pic_path, config, msg='', default=None):
    ids = config['ids']
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
        name = input('Student name or ID:').strip()
        if not name:
            if default is None:
                continue
            name = default
        if ids:
            if name in ids:
                name = ids[name]
            elif any((d in name) for d in '0123456789'):
                # This is not a student name !
                print('Unknown ID.')
                continue
        print("Name: %s" % name)
        if input("Is it correct ? (Y/n)") in ("N", "n"):
            continue
        if name:
            break
    return name






########################################################################
#                                                                      #
#                             MAIN SCRIPT                              #
#                                                                      #
########################################################################


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Extract information from numerised tests.")
    parser.add_argument('path', help=("Path to a directory which must contain "
                        "a .autoqcm.config file and a .scan.pdf file "
                        "(alternatively, this path may point to any file in this folder)."))
    group = parser.add_mutually_exclusive_group()
    # Following options can't be used simultaneously.
    group.add_argument("-p", "--page", metavar="P", type=int,
                                        help="Read only page P of pdf file.")
    group.add_argument("-sk", "--skip", "--skip-pages", metavar="P", type=int, nargs='+', default=[],
                                        help="Skip page(s) P [P ...] of pdf file.")
    parser.add_argument("-n", "--names", metavar="CSV_FILENAME", type=str,
                                        help="Read names from file CSV_FILENAME.")
    parser.add_argument("-P", "--print", action='store_true',
                        help='Print scores and solutions on default printer.')
    parser.add_argument("-m", "--mail", metavar="CSV_file",
                                                help='Mail scores and solutions.')
    parser.add_argument("--reset", action="store_true", help='Delete `scan` directory.')
    parser.add_argument("-d", "--dir", type=str,
                        help='Specify a directory with write permission.')
    parser.add_argument("-s", "--scan", "--scan-dir", type=str, metavar='DIR',
                        help='Specify the directory where the scanned tests can be found.')
    parser.add_argument("--hide-scores", action='store_true',
                help="Print only answers, not scores, in generated pdf files.")
    args = parser.parse_args()


    if any(args.path.endswith(ext) for ext in PIC_EXTS):
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

        # ------------------
        # Generate the paths
        # ------------------

        INPUT_DIR = args.scan or join(DIR, 'scan')

        # `.scan` directory is used to write intermediate files.
        # Directory tree:
        # .scan/
        # .scan/pic -> pictures extracted from the pdf
        # .scan/cfg/more_infos.csv -> missing students names.
        # .scan/scores.csv
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
        # ~ scan_pdf_path = search_by_extension(DIR, '.scan.pdf')
        scores_pdf_path = join(PDF_DIR, '%s-scores' % base_name)
        data_path = join(CFG_DIR, 'data.csv')

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
        MAX_SCORE = config['questions']*config['correct']

        if args.names is not None:
            with open(args.names, newline='') as csvfile:
                passed_names = [' '.join(row) for row in csv.reader(csvfile) if row and row[0]]
        else:
            passed_names = None

        # Extract images from all the PDF files of the input directory.
        # If images are already cached in `.scan` directory, this step will be skipped.
        pdf_files = [join(INPUT_DIR, name) for name in listdir(INPUT_DIR) if name.endswith('.pdf')]
        total_page_number = sum(number_of_pages(pdf) for pdf in pdf_files)

        if len(listdir(PIC_DIR)) != total_page_number or args.page:
            pdf2pic(*pdf_files, dest=PIC_DIR, page=args.page)

        # Read manually entered informations (if any).
        more_infos = {} # sheet_id: name
        cfg_path = join(CFG_DIR, 'more_infos.csv')
        if isfile(cfg_path):
            with open(cfg_path, 'r', newline='') as csvfile:
                reader = csv.reader(csvfile)
                for row in reader:
                    sheet_id, name = row
                    more_infos[int(sheet_id)] = name
                print("Retrieved infos:", more_infos)


        # ---------------------------------------
        # Extract informations from the pictures.
        # ---------------------------------------

        index = {}
        # `index` is used to retrieve the data associated with a name.
        # FORMAT: {name: test ID}

        pic_list = sorted(f for f in listdir(PIC_DIR)
                        if any(f.lower().endswith(ext) for ext in PIC_EXTS))

        already_seen = set()
        # Set `already_seen` will contain all seen (ID, page) couples.
        # It is used to catch an hypothetic scanning problem:
        # we have to be sure that the same page on the same test is not seen
        # twice.
        data = {}
        # Dict `data` will collect data from all scanned tests.
        #...............................................................
        # FORMAT: {ID: {'npages': (int) the number of pages seen,
        #               'score': (float) the test score,
        #               'name': (str) the student name,
        #               'pic': (str) image full path,
        #               },
        #           ...
        #          }
        #...............................................................

        for i, pic in enumerate(pic_list):
            if args.page is not None and args.page != i + 1:
                continue
            if i + 1 in args.skip:
                continue
            print('-------------------------------------------------------')
            print('Page', i + 1)
            print('File:', pic)

            # 1) Extract all the data of an image
            #    ‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾

            pic_path = join(PIC_DIR, pic)
            pic_data = scan_picture(pic_path, config)
            #...........................................................
            # `pic_data` FORMAT: {'ID': (int) ID of the test,
            #                     'page': (int) page number (for the test),
            #                     'name': (str) student name,
            #                     'score': (float) score,
            #                     }
            #...........................................................

            ID = pic_data['ID']
            p = pic_data['page']
            if (ID, p) not in already_seen:
                already_seen.add((ID, p))
            else:
                raise ValueError(f'Page {p} of test #{ID} seen twice !')

            # 2) Gather data
            #    ‾‾‾‾‾‾‾‾‾‾‾
            d = data.setdefault(ID, {'npages': 0, 'score': 0,
                                     'name': more_infos.get(ID, '')})
            d['npages'] += 1
            d['score'] += pic_data['score']
            d['pic'] = pic_path

            # 3) 1st page of the test => retrieve the student name
            #    ‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾
            if p == 1:
                # (a) The first page should contain the name
                #     ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾
                # However, if the name was already set (using `more_infos`),
                # don't overwrite it.
                if not d['name']:
                    d['name'] = pic_data['name']

                name = d['name']

                # (b) Update name manually if it was not found
                #     ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾

                if not name:
                    # (i) Test if names were passed as command line arguments.
                    if passed_names is not None:
                        if not passed_names:
                            raise RuntimeError(f'Not enough names in {args.names} !')
                        name = args.names.pop(0)
                    # (ii) If not, ask user for the name.
                    else:
                        name = read_name_manually(pic_path, config, msg=name)
                        more_infos[ID] = name
                        # Keep track of manually entered information (will be useful
                        # if `scan.py` has to be run again later !)
                        with open(cfg_path, 'a', newline='') as csvfile:
                            writerow = csv.writer(csvfile).writerow
                            writerow([str(ID), name])

                # (c) A name must not appear twice
                #     ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾

                while name in index:
                    print(f"Test #{index[name]}: {name}")
                    print(f'Test #{ID}: {name}')
                    msg = f'Error : 2 tests for same student ({name}) !\n' \
                          "Please modify at least one name (enter nothing to keep a name)."
                    # Remove twin name from index, and get the corresponding previous test ID.
                    ID0 = index.pop(name)
                    # Ask for a new name.
                    name0 = read_name_manually(data[ID0]['pic'], config, msg, default=name)
                    # Update all infos.
                    index[name0] = ID0
                    more_infos[ID0] = name0
                    data[ID0]['name'] = name0
                    # Ask for a new name for new test too.
                    name = read_name_manually(pic_path, config, default=name)
                    # Update infos
                    more_infos[ID] = name

                assert name, 'Name should not be left empty at this stage !'
                index[name] = ID
                d['name'] = name


        # ---------------------------------------------------
        # Time to synthetize & store all those informations !
        # ---------------------------------------------------

        # Names list should be empty now.
        if passed_names:
            raise RuntimeError(f'Too many names in {args.names!r} !')


        # Generate CSV file with results.
        scores = {d['name']: d['score'] for d in data.values()}
        #~ print(scores)
        scores_path = join(SCAN_DIR, 'scores.csv')
        print(f'{ANSI_CYAN}SCORES (/{MAX_SCORE:g}):{ANSI_RESET}')
        with open(scores_path, 'w', newline='') as csvfile:
            writerow = csv.writer(csvfile).writerow
            for name in sorted(scores):
                print(f' - {name}: {scores[name]:g}')
                writerow([name, scores[name]])
        mean = round(sum(scores.values())/len(scores.values()), 2)
        print(f'{ANSI_YELLOW}Mean: {mean:g}/{MAX_SCORE:g}{ANSI_RESET}')
        print(f"\nResults stored in {scores_path}\n")



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
        join_files(scores_pdf_path, pdf_paths, remove_all=True, compress=True)

        # Generate an hidden CSV file for printing or mailing results later.
        with open(data_path, 'w', newline='') as csvfile:
            writerow = csv.writer(csvfile).writerow
            for ID, d in data.items():
                #~ (identifier, answers, name, score, students, ids)
                writerow([ID, d['name'], d['score']])
        print("Data file generated for printing or mailing later.")





#m = lire_image("carres.pbm")
#print(detect_all_squares(m, size=15))
