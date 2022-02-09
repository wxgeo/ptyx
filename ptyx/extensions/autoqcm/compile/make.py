"""
Generate pdf file from raw autoqcm file.
"""
import sys
import traceback
from pathlib import Path

from ptyx.compilation import make_files, make_file
from ptyx.latex_generator import compiler
from ..tools.config_parser import dump


def generate_config_file(compiler):
    autoqcm_data = compiler.latex_generator.autoqcm_data
    file_path = compiler.file_path
    folder = file_path.parent
    name = file_path.stem
    id_table_pos = None
    for n in autoqcm_data["ordering"]:
        # XXX: what if files are not auto-numbered, but a list
        # of names is provided to Ptyx instead ?
        # (cf. command line options).
        if len(autoqcm_data["ordering"]) == 1:
            filename = f"{name}.pos"
        else:
            filename = f"{name}-{n}.pos"
        full_path = folder / ".compile" / name / filename
        d = autoqcm_data["boxes"][n] = {}
        with open(full_path) as f:
            for line in f:
                k, v = line.split(": ", 1)
                k = k.strip()
                if k == "ID-table":
                    if id_table_pos is None:
                        id_table_pos = [float(s.strip("() \n")) for s in v.split(",")]
                        autoqcm_data["id-table-pos"] = id_table_pos
                    continue
                page, x, y = [s.strip("p() \n") for s in v.split(",")]
                d.setdefault(page, {})[k] = [float(x), float(y)]

    config_file = file_path.with_suffix(".ptyx.autoqcm.config.json")
    dump(config_file, autoqcm_data)


def make(path: Path, num: int = 1, start: int = 1, quiet: bool = False) -> None:
    """Wrapper for _make(), so that `argparse` module don't intercept exceptions. """
    try:
        _make(path, num, start, quiet)
    except Exception:
        traceback.print_exc()
        print("ERROR: `autoqcm make` failed to compile document (see above fo details).")
        sys.exit(1)


def _make(path: Path, num: int = 1, start: int = 1, quiet: bool = False) -> None:
    """Implement `autoqcm make` command.
    """
    assert isinstance(num, int)
    path = path.resolve()
    all_ptyx_files = list(path.glob("*.ptyx")) if path.suffix != ".ptyx" else path
    if len(all_ptyx_files) == 0:
        raise FileNotFoundError(f"No .ptyx file found in '{path}'.")
    elif len(all_ptyx_files) > 1:
        raise FileNotFoundError(
            f"Several .ptyx file found in '{path}', I don't know which one to chose."
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
    output_name, nums = make_files(
        ptyx_filename,
        compress=True,
        number_of_documents=num,
        fixed_number_of_pages=True,
        quiet=quiet,
        start=start,
    )
    generate_config_file(compiler)

    # Keep track of the seed used.
    seed_value = compiler.seed
    seed_file_name = output_name.parent / ".seed"
    with open(seed_file_name, "w") as seed_file:
        seed_file.write(str(seed_value))

    _, nums2 = make_files(ptyx_filename, correction=True, _nums=nums, compress=True, quiet=quiet)
    assert nums2 == nums, repr((nums, nums2))

    # Generate a document including the different versions of all the questions.
    make_file(
        (output_name.parent / output_name.stem).with_suffix(".all.pdf"),
        context={"AUTOQCM_KEEP_ALL_VERSIONS": True},
        quiet=quiet,
    )
    # Generate a document including the different versions of all the questions with the correct answers checked.
    make_file(
        (output_name.parent / output_name.stem).with_suffix(".all-corr.pdf"),
        context={"AUTOQCM_KEEP_ALL_VERSIONS": True, "PTYX_WITH_ANSWERS": True},
        quiet=quiet,
    )
