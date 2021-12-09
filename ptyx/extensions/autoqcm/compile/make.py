"""
Generate pdf file from raw autoqcm file.
"""

from pathlib import Path

from ptyx.compilation import make_files
from ptyx.latexgenerator import compiler


def make(pth: str = '.', num: int = 1) -> None:
    """Implement `autoqcm make` command.
    """
    pth = Path(pth).resolve()
    if pth.suffix != ".ptyx":
        all_ptyx_filenames = list(pth.glob("*.ptyx"))
    if len(ptyx_file) == 0:
        raise FileNotFoundError(f"No .ptyx file found in '{pth}'.")
    elif len(ptyx_file) > 1:
        raise FileNotFoundError(f"Several .ptyx file found in '{pth}', I don't know which to chose.")
    ptyx_filename = all_ptyx_filenames[0]
    # Read pTyX file.
    print(f"Reading {ptyx_filename}...")
    compiler.read_file(ptyx_filename)
    # Parse #INCLUDE tags, load extensions if needed, read seed.
    compiler.preparse()

    # Generate syntax tree.
    # The syntax tree is generated only once, and will then be used
    # for all the following compilations.
    compiler.generate_syntax_tree()

    # Compile and generate output files (tex or pdf)
    filenames, output_name, nums = make_files(ptyx_filename, **vars(options))

    # Keep track of the seed used.
    seed_value = compiler.seed
    seed_file_name = os.path.join(os.path.dirname(output_name), ".seed")
    with open(seed_file_name, "w") as seed_file:
        seed_file.write(str(seed_value))

    filenames, output_name, nums2 = make_files(
        ptyx_filename, correction=True, _nums=nums
    )
    assert nums2 == nums, repr((nums, nums2))

    compiler.close()

