#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Oct 23 22:54:07 2020

@author: nicolas
"""

import subprocess
from shutil import rmtree
from os import listdir, mkdir, rename
from os.path import join, basename


PIC_EXTS = (".jpg", ".jpeg", ".png")


def run(cmd):
    "Run command as a subprocess, raising an Python error if it fails."
    return subprocess.run(cmd, check=True, stdout=subprocess.PIPE)


def _extract_pictures(pdf_path, dest, page=None):
    "Extract all pictures from pdf file in given `dest` directory. "
    # pdfimages `-all` : keep image native format (for jpg, png ans some other formats).
    cmd = ["pdfimages", "-all", pdf_path, join(dest, "pic")]
    if page is not None:
        p = str(page)
        cmd = cmd[:1] + ["-f", p, "-l", p] + cmd[1:]
    # ~ print(cmd)
    run(cmd)


def _export_pdf_to_jpg(pdf_path, dest, page=None):
    print("Convert PDF to JPG, please wait...")
    cmd = [
        "gs",
        "-dNOPAUSE",
        "-dBATCH",
        "-sDEVICE=jpeg",
        "-r200",
        "-sOutputFile=" + join(dest, "%03d.jpg"),
        pdf_path,
    ]
    if page is not None:
        cmd = cmd[:1] + ["-dFirstPage=%s" % page, "-dLastPage=%s" % page] + cmd[1:]
    run(cmd)


def extract_pdf_pictures(pdf_file: str, dest: str, page=None):
    "Clear `dest` folder, then extract all pages of the pdf files inside."
    rmtree(dest, ignore_errors=True)
    mkdir(dest)
    tmp_dir = join(dest, ".tmp")
    print(f"Extracting all images from {basename(pdf_file)!r}, please wait...")
    rmtree(tmp_dir, ignore_errors=True)
    mkdir(tmp_dir)
    _extract_pictures(pdf_file, tmp_dir, page)
    # PDF may contain special files (OCR...) we can't handle.
    # In that case, we will rasterize pdf, using Ghostscript.
    pics = listdir(tmp_dir)
    if not all(any(f.endswith(ext) for ext in PIC_EXTS) for f in pics):
        rmtree(tmp_dir)
        mkdir(tmp_dir)
        _export_pdf_to_jpg(pdf_file, tmp_dir, page)
        pics = listdir(tmp_dir)
    for pic in pics:
        rename(join(tmp_dir, pic), join(dest, pic))
    rmtree(tmp_dir)


# def pdf2pic(*pdf_files: str, dest: str, page=None):
#    "Clear `dest` folder, then extract all pages of the pdf files inside."
#    rmtree(dest)
#    mkdir(dest)
#    tmp_dir = join(dest, '.tmp')
#    for pdf in pdf_files:
#        print(f'Extracting all images from {basename(pdf)!r}, please wait...')
#        rmtree(tmp_dir, ignore_errors=True)
#        mkdir(tmp_dir)
#        _extract_pictures(pdf, tmp_dir, page)
#        # PDF may contain special files (OCR...) we can't handle.
#        # In that case, we will rasterize pdf, using Ghostscript.
#        pics = listdir(tmp_dir)
#        if not all(any(f.endswith(ext) for ext in PIC_EXTS) for f in pics):
#            rmtree(tmp_dir)
#            mkdir(tmp_dir)
#            _export_pdf_to_jpg(pdf, tmp_dir, page)
#            pics = listdir(tmp_dir)
#        for pic in pics:
#            rename(join(tmp_dir, pic), join(dest, f'f-{pdf}-{pic}'))
#    rmtree(tmp_dir)
#
# def extract_pictures_from_pdf(source: str, dest: str):
#    "Extract in `dest` directory all pictures from the pdf files found in the" \
#    "`source` directory."
#    # If images are already cached in `.scan` directory, this step will be skipped.
#    pdf_files = glob(join(source, '**/*.pdf'), recursive=True)
#    # ~ pdf_files = [join(INPUT_DIR, name) for name in listdir(INPUT_DIR) if name.endswith('.pdf')]
#    total_page_number = sum(number_of_pages(pdf) for pdf in pdf_files)
#
#    if len(listdir(dest)) != total_page_number:
#        pdf2pic(*pdf_files, dest=dest)
#    else:
#        print("Info: No new pdf file detected.")


def number_of_pages(pdf_path: str) -> int:
    "Return the number of pages of the pdf."
    cmd = ["pdfinfo", pdf_path]
    # An example of pdfinfo output:
    # ...
    # JavaScript:     no
    # Pages:          19
    # Encrypted:      no
    # ...
    l = run(cmd).stdout.decode("utf-8").split()
    return int(l[l.index("Pages:") + 1])
