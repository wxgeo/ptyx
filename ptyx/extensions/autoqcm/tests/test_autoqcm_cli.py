"""
Test autoqcm command line interface.

Test new, make and scan subcommands.
"""

import tempfile
from os.path import join
from os import listdir
import csv
from pathlib import Path
from shutil import rmtree

from PIL import ImageDraw
from pdf2image import convert_from_path

from ptyx.extensions.autoqcm.cli import main
from ptyx.extensions.autoqcm.scan.square_detection import COLORS
from ptyx.extensions.autoqcm.tools.config_parser import load, is_answer_correct
from ptyx.extensions.autoqcm.parameters import CELL_SIZE_IN_CM


INCH2CM = 2.54
DPI = 200
CELL_SIZE_IN_PX = CELL_SIZE_IN_CM/INCH2CM*DPI


def _fill_checkbox(draw, pos, size):
    i, j = pos
    blue = COLORS["blue"]
    # Draw a blue square around the box (for debugging purpose).
    draw.rectangle((j, i, j + size, i + size), fill=blue)
    draw.rectangle((0, 0, 200, 200), fill=COLORS["red"])


def simulate_answer(pics, config):
    """Amend answer sheet with scores and correct answers.

    `data` is the dict generated when the answer sheet is scanned.
    `ID` is the ID of answer sheet.
    """
    # Convert cell size from cm to pixels
    pic_num = 0
    for doc_id, data in config['boxes'].items():
        for page, page_data in data.items():
            pic = pics[pic_num]
            # Convert to RGB picture.
#            pic = pic_parser.get_pic(ID, page).convert("RGB")
            # Drawing context
            draw = ImageDraw.Draw(pic)
            for q_a, pos in page_data.items():
                q, a = map(int, q_a[1:].split('-'))
                _fill_checkbox(draw, pos, CELL_SIZE_IN_PX)
                return pics
#                if is_answer_correct(q, a, config, doc_id):
#                    _fill_checkbox(draw, pos, size)
            pic_num += 1
    return pics




def test_cli():
    students = {12345678: "Jean Dupond", 34567890: "Martin De La Tour"}
    # Make a temporary directory
    with tempfile.TemporaryDirectory() as parent:
        parent = Path("/tmp")
        rmtree("/tmp/mcq", ignore_errors=True)
        print(10*"=")
        print(parent)
        print(10*"=")
        parent = Path(parent)
        with open(parent / "students.csv", "w", newline='') as csvfile:
            csv.writer(csvfile).writerows(students.items())

        path = parent / "mcq"

        # Test autoqcm new
        main(["new", str(path)])
        assert "new.ptyx" in listdir(path)

        with open(path / "new.ptyx") as ptyxfile:
            ptyxfile_content = ptyxfile.read()
        with open(path / "new.ptyx", "w") as ptyxfile:
            assert "\nid format" in ptyxfile_content
            ptyxfile_content.replace("\nid format", "\nids=../students.csv\nid format")
            ptyxfile.write(ptyxfile_content)

        # Test autoqcm make
        main(["make", str(path), "-n", "2"])
        assert "new.pdf" in listdir(path)
        assert "new-corr.pdf" in listdir(path)
        # TODO: assert "new.all.pdf" in listdir(path)

        # Test autoqcm scan
        images = convert_from_path(path / 'new.pdf', dpi=DPI, output_folder=path)
        config = load(path / 'new.ptyx.autoqcm.config.json')
        images = simulate_answer(images, config)
        images[0].save(
            path / "scan/simulate-scan.pdf",
            save_all=True,
            append_images=images[1:],
        )
        main(["scan", str(path)])


if __name__ == "__main__":
    test_cli()
