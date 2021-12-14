"""
Generate pdf file from raw autoqcm file.
"""
from pathlib import Path

from ptyx.compilation import make_files, make_file
from ptyx.latexgenerator import compiler


def make(pth: str = ".", num: int = 1) -> None:
    """Implement `autoqcm make` command.
    """
    pth = Path(pth).resolve()
    all_ptyx_files = list(pth.glob("*.ptyx")) if pth.suffix != ".ptyx" else pth
    if len(all_ptyx_files) == 0:
        raise FileNotFoundError(f"No .ptyx file found in '{pth}'.")
    elif len(all_ptyx_files) > 1:
        raise FileNotFoundError(
            f"Several .ptyx file found in '{pth}', I don't know which to chose."
        )
    ptyx_filename = all_ptyx_files[0]
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
    _, output_name, nums = make_files(ptyx_filename, compress=True, number=num, same_pages_number=True)

    # Keep track of the seed used.
    seed_value = compiler.seed
    seed_file_name = output_name.parent / ".seed"
    with open(seed_file_name, "w") as seed_file:
        seed_file.write(str(seed_value))

    _, _, nums2 = make_files(ptyx_filename, correction=True, _nums=nums, compress=True)
    assert nums2 == nums, repr((nums, nums2))

    pdf_with_all_versions = (output_name.parent / output_name.stem).with_suffix(".all.pdf")
    make_file(pdf_with_all_versions, context={'AUTOQCM_KEEP_ALL_VERSIONS': True})
    compiler.close()
