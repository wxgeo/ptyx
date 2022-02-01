#!/usr/bin/env python3

# -----------------------------------------
#                  Scan
#     Extract info from digitized documents
# -----------------------------------------
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
from time import strftime
from typing import Iterator
from math import inf
from typing import Union, Literal, Optional

from PIL import Image
from numpy import int8, array, ndarray

# File `compilation.py` is in ../.., so we have to "hack" `sys.path` a bit.
# script_path = dirname(abspath(sys._getframe().f_code.co_filename))
# sys.path.insert(0, join(script_path, '../..'))

from ..compile.header import answers_and_score
from ..tools.config_parser import load, get_correct_answers
from .scan_pic import (
    scan_picture,
    ANSI_YELLOW,
    ANSI_RESET,
    ANSI_CYAN,
    ANSI_GREEN,
    ANSI_RED,
    color2debug,
    CalibrationError,
)
from .amend import amend_all
from .pdftools import extract_pdf_pictures, PIC_EXTS, number_of_pages
from .tools import search_by_extension, print_framed_msg
from ptyx.compilation import join_files, compile_latex




def pic_names_iterator(data: dict) -> Iterator[Path]:
    """Iterate over all pics found in data (i.e. all the pictures already analysed)."""
    for d in data.values():
        for pic_data in d["pages"].values():
            path = Path(pic_data["pic_path"])
            # return pdfhash/picnumber.png
            yield path.relative_to(path.parent.parent)


class MCQPictureParser:
    """Main class for parsing pdf files containing all the scanned MCQ."""

    def __init__(
        self,
        path: Union[str, Path],
        input_dir: Optional[Path] = None,
        output_dir: Optional[Path] = None,
    ):
        self.path = Path(path).expanduser().resolve()
        # Main paths.
        self.dirs = {}
        self.files = {}
        # All data extracted from pdf files.
        self.data = {}
        # Additional informations entered manually.
        self.more_infos = {}  # sheet_id: (name, student_id)
        self.config = {}
        # Manually verified pages.
        self.verified = set()
        # `name2sheetID` is used to retrieve the data associated with a name.
        # FORMAT: {name: test ID}
        self.name2sheetID = {}
        # Set `already_seen` will contain all seen (ID, page) couples.
        # It is used to catch an hypothetical scanning problem:
        # we have to be sure that the same page on the same test is not seen
        # twice.
        self.already_seen = set()
        self.skipped = set()
        self.warnings = False
        self.logname = strftime("%Y.%m.%d-%H.%M.%S") + ".log"
        self.correct_answers = {}
        self._generate_paths(input_dir, output_dir)
        self._load_configuration()

    def _load_data(self):
        if self.dirs["data"].is_dir():
            for filename in self.dirs["data"].glob("*/*.scandata"):
                ID = int(filename.stem)
                with open(filename) as f:
                    try:
                        self.data[ID] = literal_eval(f.read())
                    except ValueError as e:
                        # Temporary patch.
                        # set() is not supported by literal_eval() until Python 3.9
                        # XXX: remove this once Ubuntu 22.04 will be released.
                        f.seek(0)
                        s = f.read()
                        if sys.version_info < (3, 9) and "set()" in s:
                            self.data[ID] = eval(s)
                        else:
                            print(f"ERROR when reading {filename} :")
                            raise e
                    except Exception:
                        print(f"ERROR when reading {filename} :")
                        raise

    def _store_data(self, pdf_hash: str, doc_id, p, matrix=None):
        folder = self.dirs["data"] / pdf_hash
        folder.mkdir(exist_ok=True)
        with open(folder / f"{doc_id}.scandata", "w") as f:
            f.write(repr(self.data[doc_id]))
        # We will store a compressed version of the matrix.
        # (It would consume too much memory else).
        if matrix is not None:
            webp = folder / f"{doc_id}-{p}.webp"
            Image.fromarray((255 * matrix).astype(int8)).save(str(webp), format="WEBP")

    def get_pic(self, doc_id, p, as_matrix=False):
        webp = next(self.dirs["data"].glob(f"*/{doc_id}-{p}.webp"))
        im = Image.open(str(webp))
        if as_matrix:
            return array(im.convert("L")) / 255
        return im

    def _read_name_manually(self, doc_id, matrix=None, p=None, default=None):
        if matrix is None:
            matrix = self.get_pic(doc_id, p, as_matrix=True)
        student_ids = self.config["ids"]
        student_ID = ""
        print("Name can not be read automatically.")
        print("Please read the name on the picture which will be displayed now.")
        input("-- Press enter --")
        #    subprocess.run(["display", "-resize", "1920x1080", pic_path])
        # TODO: use first letters of students name to find student.
        # (ask again if not found, or if several names match first letters)
        process = None
        while True:
            nlines = matrix.shape[1]
            # Don't relaunch process if it is still alive.
            # (process.poll() is not None for dead processes.)
            if process is None or process.poll() is not None:
                process = color2debug(matrix[0 : int(3 / 4 * nlines), :], wait=False)
            name = input("Student name or ID:").strip()
            if not name:
                if default is None:
                    continue
                name = default
            if student_ids:
                if name in student_ids:
                    name, student_ID = student_ids[name], name
                elif any((d in name) for d in "0123456789"):
                    # This is not a student name !
                    print("Unknown ID.")
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
        with open(self.files["cfg"], "a", newline="") as csvfile:
            writerow = csv.writer(csvfile).writerow
            writerow([str(doc_id), name, student_ID])
        return name, student_ID

    def _test_integrity(self):
        """For every test:
        - all pages must have been scanned,
        - all questions must have been seen."""
        questions_not_seen = {}
        pages_not_seen = {}
        for ID in self.data:
            questions = set(self.config["ordering"][ID]["questions"])
            diff = questions - set(self.data[ID]["answered"])
            if diff:
                questions_not_seen[ID] = ", ".join(str(q) for q in diff)
            # All tests may not have the same number of pages, since
            # page breaking will occur at a different place for each test.
            pages = set(self.config["boxes"][ID])
            diff = pages - set(self.data[ID]["pages"])
            if diff:
                pages_not_seen[ID] = ", ".join(str(p) for p in diff)
        if pages_not_seen:
            self._warn("= WARNING =")
            self._warn("Pages not seen:")
            for ID in sorted(pages_not_seen):
                self._warn(f"    • Test {ID}: page(s) {pages_not_seen[ID]}")
        if questions_not_seen:
            self._warn("=== ERROR ===")
            self._warn("Questions not seen !")
            for ID in sorted(questions_not_seen):
                self._warn(f"    • Test {ID}: question(s) {questions_not_seen[ID]}")

        if questions_not_seen:
            # Don't raise an error for pages not found (only a warning in log)
            # if all questions were found, this was probably empty pages.
            raise RuntimeError(f"Questions not seen ! (Look at message above).")

    def _keep_previous_version(self, pic_data: dict) -> bool:
        """Test if a previous version of the same page exist.

        If so, it probably means the page has been scanned twice, but it could
        also indicate a more serious problem (for example, tests with the same ID
        have been given to different students !).
        As a precaution, we should signal the problem to the user, and ask him
        what he wants to do.
        """
        ID = pic_data["ID"]
        p = pic_data["page"]

        # This page has never been seen before, everything is OK.
        if (ID, p) not in self.already_seen:
            self.already_seen.add((ID, p))
            return False

        # This is problematic: it seems like the same page has been seen twice.
        lastpic_path = pic_data["pic_path"]
        lastpic = Path(lastpic_path).relative_to(self.dirs["pic"])
        firstpic_path = self.data[ID]["pages"][p]["pic_path"]
        firstpic = Path(firstpic_path).relative_to(self.dirs["pic"])
        assert isinstance(lastpic_path, str)
        assert isinstance(firstpic_path, str)

        self._warn(
            f"WARNING: Page {p} of test #{ID} seen twice " f'(in "{firstpic}" and "{lastpic}") !'
        )
        action = None
        keys = ("name", "student_ID", "answered")
        if all(pic_data[key] == self.data[ID]["pages"][p][key] for key in keys):
            # Same information found on the two pages, just keep one version.
            action = "f"
            self._warn("Both page have the same information, keeping only first one...")

        # We have a problem: this is a duplicate.
        # In other words, we have 2 different versions of the same page.
        # Ask the user what to do.
        while action not in ("f", "l"):
            print("What must we do ?")
            print("- See pictures (s)")
            print("- Keep only first one (f)")
            print("- Keep only last one (l)")

            action = input("Answer:")
            if action == "s":
                with tempfile.TemporaryDirectory() as tmpdirname:
                    path = Path(tmpdirname) / "test.png"
                    # https://stackoverflow.com/questions/39141694/how-to-display-multiple-images-in-unix-command-line
                    subprocess.run(
                        ["convert", firstpic_path, lastpic_path, "-append", str(path)], check=True
                    )
                    subprocess.run(["feh", "-F", str(path)], check=True)
                    input("-- pause --")
        # We must memorize which version should be skipped in case user
        # launch scan another time.
        skipped_pic = firstpic if action == "l" else lastpic
        with open(self.files["skipped"], "a", newline="", encoding="utf8") as file:
            file.write(f"{skipped_pic}\n")

        if action == "l":
            # Remove first picture information.
            del self.data[ID]["pages"][p]
            self._store_data(firstpic.parent.name, ID, p)

        return action == "f"

    def _extract_name(self, doc_id: str, d: dict, matrix: ndarray, ask: bool = False):
        # TODO: what is matrix type ?
        pic_data = d["pages"][1]
        # (a) The first page should contain the name
        #     ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾
        # However, if the name was already set (using `more_infos`),
        # don't overwrite it.
        if not d["name"]:
            # Store the name read (except if ask not to do so).
            if not ask:
                d["name"] = pic_data["name"]

        name = d["name"]

        # (b) Update name manually if it was not found
        #     ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾

        if not name:
            name = self._read_name_manually(doc_id, matrix)[0]

        # (c) A name must not appear twice
        #     ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾ ‾
        while name in self.name2sheetID:
            print(f"Test #{self.name2sheetID[name]}: {name}")
            print(f"Test #{doc_id}: {name}")
            print_framed_msg(
                f"Error : 2 tests for same student ({name}) !\n"
                "Please modify at least one name (enter nothing to keep a name)."
            )
            # Remove twin name from name2sheetID, and get the corresponding previous test ID.
            ID0 = self.name2sheetID.pop(name)
            # Ask for a new name.
            name0, student_ID0 = self._read_name_manually(ID0, p=1, default=name)
            # Update all infos.
            self.name2sheetID[name0] = ID0
            self.data[ID0]["name"] = name0
            self.data[ID0]["student_ID"] = student_ID0
            # Ask for a new name for new test too.
            name = self._read_name_manually(doc_id, matrix, default=name)[0]

        assert name, "Name should not be left empty at this stage !"
        self.name2sheetID[name] = doc_id
        d["name"] = name

    def _calculate_scores(self):
        cfg = self.config
        default_mode = cfg["mode"]["default"]
        default_correct = cfg["correct"]["default"]
        default_incorrect = cfg["incorrect"]["default"]
        default_skipped = cfg["skipped"]["default"]

        for ID in self.data:
            correct_ans = self.correct_answers[ID]
            print(f'Test {ID} - {self.data[ID]["name"]}')
            d = self.data[ID]
            for q in sorted(d["answered"]):
                answered = set(d["answered"][q])
                correct_ones = correct_ans[q]
                mode = cfg["mode"].get(q, default_mode)

                if mode == "all":
                    ok = answered == correct_ones
                elif mode == "some":
                    # Answer is valid if and only if :
                    # (proposed ≠ ∅ and proposed ⊆ correct) or (proposed = correct = ∅)
                    ok = (answered and answered.issubset(correct_ones)) or (
                        not answered and not correct_ones
                    )
                elif mode == "skip":
                    print(f"Question {q} skipped...")
                    continue
                else:
                    raise RuntimeError("Invalid mode (%s) !" % mode)
                if ok:
                    earn = float(cfg["correct"].get(q, default_correct))
                    color = ANSI_GREEN
                elif not answered:
                    earn = float(cfg["skipped"].get(q, default_skipped))
                    color = ANSI_YELLOW
                else:
                    earn = float(cfg["incorrect"].get(q, default_incorrect))
                    color = ANSI_RED
                print(f"-  {color}Rating (Q{q}): {color}{earn:g}{ANSI_RESET}")
                d["score"] += earn
                d["score_per_question"][q] = earn

    def generate_output(self):
        """Generate CSV files with scores and annotated documents."""
        max_score = self.config["max_score"]
        # Generate CSV file with results.
        scores = {d["name"]: d["score"] for d in self.data.values()}
        # ~ print(scores)
        scores_path = self.dirs["output"] / "scores.csv"
        print(f"{ANSI_CYAN}SCORES (/{max_score:g}):{ANSI_RESET}")
        with open(scores_path, "w", newline="") as csvfile:
            writerow = csv.writer(csvfile).writerow
            writerow(("Name", "Score"))
            for name in sorted(scores):
                print(f" - {name}: {scores[name]:g}")
                writerow([name, scores[name]])
        if scores.values():
            mean = round(sum(scores.values()) / len(scores.values()), 2)
            print(f"{ANSI_YELLOW}Mean: {mean:g}/{max_score:g}{ANSI_RESET}")
        else:
            print("No score found !")
        print(f'\nResults stored in "{scores_path}"\n')

        # Generate CSV file with ID and pictures names for all students.
        info_path = self.dirs["output"] / "infos.csv"
        info = [
            (
                d["name"],
                d["student_ID"],
                ID,
                d["score"],
                [d["pages"][p]["pic_path"] for p in d["pages"]],
            )
            for ID, d in self.data.items()
        ]
        print(f"{ANSI_CYAN}SCORES (/{max_score:g}):{ANSI_RESET}")
        with open(info_path, "w", newline="") as csvfile:
            writerow = csv.writer(csvfile).writerow
            writerow(("Name", "Student ID", "Test ID", "Score", "Pictures"))
            for name, student_ID, doc_id, score, paths in sorted(info):
                paths = ", ".join(str(pth) for pth in paths)
                writerow([name, student_ID, f"#{doc_id}", score, paths])
        print(f'Infos stored in "{info_path}"\n')
        amend_all(self)

    def generate_correction(self, display_score: bool = True) -> None:
        """Generate pdf files, with the score and the table of correct answers for each test."""
        pdf_paths = []
        for doc_id, d in self.data.items():
            # ~ identifier, answers, name, score, students, ids
            name = d["name"]
            score = d["score"]
            path = self.dirs["pdf"] / "%s-%s-corr.score" % (self.files["base"], doc_id)
            pdf_paths.append(path)
            print(f"Generating pdf file for student {name} (subject {doc_id}, score {score})...")
            latex = answers_and_score(self.config, name, doc_id, (score if display_score else None))
            texfile_name = path.with_suffix(".tex")
            with open(texfile_name, "w") as texfile:
                texfile.write(latex)
                texfile.flush()
            compile_latex(texfile_name, dest=path, quiet=True)
        join_files(self.files["results"], pdf_paths, remove_all=True, compress=True)

    def _load_configuration(self):
        """Read configuration file, load configuration and calculate maximal score too."""
        configfile = search_by_extension(self.path, ".autoqcm.config.json")
        cfg = load(configfile)
        self.correct_answers = get_correct_answers(cfg)
        default_mode = cfg["mode"]["default"]
        default_correct = cfg["correct"]["default"]

        max_score = 0
        # Take a random student test, and calculate max score for it.
        # Maximal score = (number of questions)x(score when answer is correct)
        for q in next(iter(cfg["ordering"].values()))["questions"]:
            q = str(q)
            if cfg["mode"].get(q, default_mode) != "skip":
                max_score += int(cfg["correct"].get(q, default_correct))
        cfg["max_score"] = max_score
        self.config = cfg

    def _make_dirs(self, reset: bool = False):
        """Generate output directory structure.

        If `reset` is True, remove all output directory content.
        """
        if reset and self.dirs["output"].is_dir():
            rmtree(self.dirs["output"])

        for directory in self.dirs.values():
            if not directory.is_dir():
                directory.mkdir()

    def _generate_paths(self, input_dir: Optional[Path] = None, output_dir: Optional[Path] = None):
        root = self.path
        if not root.is_dir():
            root = root.parent
            if not root.is_dir():
                raise FileNotFoundError("%s does not seem to be a directory !" % root)
        self.dirs["root"] = root

        # ------------------
        # Generate the paths
        # ------------------

        self.dirs["input"] = input_dir or (root / "scan")

        # `.scan` directory is used to write intermediate files.
        # Directory tree:
        # .scan/
        # .scan/pic -> pictures extracted from the pdf
        # .scan/cfg/more_infos.csv -> missing students names.
        # .scan/cfg/verified.csv -> pages already verified.
        # .scan/cfg/skipped.csv -> pages to skip.
        # .scan/scores.csv
        # .scan/data -> data stored as .scandata files (used to resume interrupted scan).
        self.dirs["output"] = output_dir or (self.dirs["root"] / ".scan")
        self.dirs["data"] = self.dirs["output"] / "data"
        self.dirs["cfg"] = self.dirs["output"] / "cfg"
        self.dirs["pic"] = self.dirs["output"] / "pic"
        self.dirs["pdf"] = self.dirs["output"] / "pdf"
        self.dirs["log"] = self.dirs["output"] / "log"

        self.files["base"] = search_by_extension(self.dirs["root"], ".ptyx").stem
        self.files["results"] = self.dirs["pdf"] / (self.files["base"] + "-results")

    #    def _extract_pictures_from_pdf(self):
    #        # First, we must test if pdf files have changed.
    #        # - calculate hash for each file.
    #        # - if nothing has changes, pass.
    #        # - if new pdf files are found, extract pictures from them and store their hash.
    #        # - if pdf files where modified or removed, regenerate everything.
    #        # hashlib.sha512(f.read()).hexdigest()

    def _load_all_info(self):
        """Load all informations from files."""
        self._load_data()

        # Read manually entered informations (if any).
        self.files["cfg"] = self.dirs["cfg"] / "more_infos.csv"
        if self.files["cfg"].is_file():
            with open(self.files["cfg"], "r", newline="") as csvfile:
                reader = csv.reader(csvfile)
                for row in reader:
                    try:
                        sheet_ID, name, student_ID = row
                    except ValueError:
                        sheet_ID, name = row
                        student_ID = ""
                    self.more_infos[int(sheet_ID)] = (name, student_ID)
                print("Retrieved infos:", self.more_infos)

        # List manually verified pages.
        # They should not be verified anymore.
        self.files["verified"] = self.dirs["cfg"] / "verified.txt"
        if self.files["verified"].is_file():
            with open(self.files["verified"], "r", encoding="utf8", newline="") as file:
                self.verified = set(Path(line.strip()) for line in file.readlines())
                print("Pages manually verified:")
                for path in self.verified:
                    print(f"    • {path}")

        self.skipped = set(pic_names_iterator(self.data))

        # List skipped pictures.
        # Next time, they will be skipped with no warning.
        self.files["skipped"] = self.dirs["cfg"] / "skipped.txt"
        if self.files["skipped"].is_file():
            with open(self.files["skipped"], "r", encoding="utf8", newline="") as file:
                self.skipped |= set(Path(line.strip()) for line in file.readlines())
                print("Pictures skipped:")
                for path in sorted(self.skipped):
                    print(f"    • {path}")

    def scan_picture(self, picture: Union[str, Path], manual_verification: bool = True) -> None:
        """This is used for debuging (it allows to test pages one by one)."""
        # f1-pic-003.jpg (page 25)
        # f12-pic-005.jpg
        # f12-pic-003.jpg
        # f12-pic-004.jpg
        # f12-pic-013.jpg
        # f7-pic-013.jpg
        # f9-pic-004.jpg
        # f9-pic-005.jpg
        # f13-pic-002.jpg
        if not any(str(picture).endswith(ext) for ext in PIC_EXTS):
            raise TypeError("Allowed picture extensions: " + ", ".join(PIC_EXTS))
        pic_path = Path(picture).expanduser().resolve()
        if not pic_path.is_file():
            pic_path = self.dirs["pic"] / picture
        pic_data, _ = scan_picture(pic_path, self.config, manual_verification=manual_verification)
        print(pic_data)

    def _generate_current_pdf_hashes(self) -> dict:
        """Return the hashes of all the pdf files found in `scan/` directory.

        Return: {hash: pdf path}
        """
        hashes = dict()
        for path in self.dirs["input"].glob("*.pdf"):
            with open(path, "rb") as pdf_file:
                hashes[blake2b(pdf_file.read(), digest_size=20).hexdigest()] = path
        return hashes

    def _update_input_data(self):
        """Test if input data has changed, and update it if needed."""
        hash2pdf: dict = self._generate_current_pdf_hashes()

        def test_path(pth):
            if not pth.is_dir():
                raise RuntimeError(
                    f'Folder "{pth.parent}" should only contain folders.\n'
                    "You may clean it manually, or remove it with following command:\n"
                    f'rm -r "{pth.parent}"'
                )

        # For each removed pdf files, remove corresponding pictures and data
        for path in self.dirs["pic"].iterdir():
            test_path(path)
            if path.name not in hash2pdf:
                rmtree(path)
        for path in self.dirs["data"].iterdir():
            test_path(path)
            if path.name not in hash2pdf:
                rmtree(path)

        # For each new pdf files, extract all pictures
        for pdfhash, pdfpath in hash2pdf.items():
            folder = self.dirs["pic"] / pdfhash
            if not folder.is_dir():
                extract_pdf_pictures(pdfpath, folder)
            elif number_of_pages(pdfpath) != len(
                [f for f in folder.iterdir() if f.suffix.lower() in PIC_EXTS]
            ):
                # Extraction was probably interrupted
                rmtree(folder)
                folder.mkdir()
                extract_pdf_pictures(pdfpath, folder)

    def _warn(self, *values, sep=" ", end="\n"):
        """Print to stdout and write to log file."""
        msg = sep.join(str(val) for val in values) + end
        print(msg)
        with open(self.dirs["log"] / self.logname, "a", encoding="utf8") as logfile:
            logfile.write(msg)
        self.warnings = True

    def scan_all(
        self,
        start: int = 1,
        end: Union[int, float] = inf,
        manual_verification: Optional[bool] = None,
        ask_for_name: bool = False,
        reset: bool = False,
    ):
        """Extract information from pdf, calculate scores and annotate documents
        to display correct answers."""
        self._make_dirs(reset)

        # Test if the PDF files of the input directory have changed and
        # extract the images from the PDF files if needed.
        self._update_input_data()
        # Load data from previous run
        self._load_all_info()

        # Dict `data` will collect data from all scanned tests.
        # ...............................................................
        # FORMAT: {ID: {'pages': (dict) the pages seen, and all related information,
        #               'answers': ({int: set}) the answers of the student for each question,
        #               'score': (float) the test score,
        #               'name': (str) the student name,
        #               'last_pic': (str) last image seen full path,
        #               },
        #           ...
        #          }
        # ...............................................................
        #

        # ---------------------------------------
        # Extract informations from the pictures.
        # ---------------------------------------
        data = self.data
        self.name2sheetID = {d["name"]: ID for ID, d in data.items()}
        self.already_seen = set((ID, p) for ID, d in data.items() for p in d["pages"])
        pic_list = sorted(f for f in self.dirs["pic"].glob("*/*") if f.suffix.lower() in PIC_EXTS)

        assert all(isinstance(path, Path) for path in self.skipped)
        assert all(isinstance(path, Path) for path in self.verified)

        for i, pic_path in enumerate(pic_list, start=1):
            if not (start <= i <= end):
                continue
            # Make pic_path relative, so that folder may be moved if needed.
            pic_path = pic_path.relative_to(self.dirs["pic"])
            if pic_path in self.skipped:
                continue
            print("-------------------------------------------------------")
            print("Page", i)
            print("File:", pic_path)

            # 1) Extract all the data of an image
            #    ‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾

            try:
                # Warning: manual_verification can be None, so the order is important
                # below : False and None -> False (but None and False -> None).
                manual_verification = (pic_path not in self.verified) and manual_verification
                pic_data, matrix = scan_picture(
                    self.dirs["pic"] / pic_path, self.config, manual_verification
                )
                # `pic_data` FORMAT is specified in `scan_pic.py`.
                # (Search for `pic_data =` in `scan_pic.py`).
                pic_data["pic_path"] = str(pic_path)
                print()

            except CalibrationError:
                self._warn(f"WARNING: {pic_path} seems invalid ! Skipping...")
                input("-- PAUSE --")
                with open(self.files["skipped"], "a", newline="", encoding="utf8") as file:
                    file.write(f"{pic_path}\n")
                continue

            if pic_data["verified"]:
                # If the page has been manually verified, keep track of it,
                # so it won't be verified next time if a second pass is needed.
                with open(self.files["verified"], "a", newline="", encoding="utf8") as file:
                    file.write(f"{pic_path}\n")

            ID = pic_data["ID"]
            page = pic_data["page"]

            if self._keep_previous_version(pic_data):
                continue

            # 2) Gather data
            #    ‾‾‾‾‾‾‾‾‾‾‾
            name, student_ID = self.more_infos.get(ID, ("", ""))
            data_for_this_ID = data.setdefault(
                ID,
                {
                    "pages": {},
                    "name": name,
                    "student_ID": student_ID,
                    "answered": {},
                    "score": 0,
                    "score_per_question": {},
                },
            )
            data_for_this_ID["pages"][page] = pic_data

            for q in pic_data["answered"]:
                ans = data_for_this_ID["answered"].setdefault(q, set())
                ans |= pic_data["answered"][q]

            # 3) 1st page of the test => retrieve the student name
            #    ‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾
            if page == 1:
                self._extract_name(ID, data_for_this_ID, matrix)

            # Store work in progress, so we can resume process if something fails...
            self._store_data(pic_path.parent.name, ID, page, matrix)

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
        self.generate_output()

    def resolve_conflicts(self):
        """Resolve conflicts manually: unknown student ID, ambiguous answer..."""
        pass


def scan(
    path: Path,
    reset: bool = False,
    ask_for_name: bool = False,
    verify: Literal["auto", "always", "never"] = "auto",
) -> None:
    """Implement `autoqcm scan` command."""
    if verify == "always":
        manual_verification: Optional[bool] = True
    elif verify == "never":
        manual_verification = False
    else:
        manual_verification = None
    MCQPictureParser(path).scan_all(
        reset=reset, ask_for_name=ask_for_name, manual_verification=manual_verification
    )
