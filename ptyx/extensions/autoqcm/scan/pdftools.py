#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Oct 23 22:54:07 2020

@author: nicolas
"""

import subprocess
from os.path import join, basename
from shutil import rmtree
from os import listdir, mkdir, rename

PIC_EXTS = ('.jpg', '.jpeg', '.png')


def _extract_pictures(pdf_path, dest, page=None):
    "Extract all pictures from pdf file in given `dest` directory. "
    cmd = ["pdfimages", "-all", pdf_path, join(dest, 'pic')]
    if page is not None:
        p = str(page)
        cmd = cmd[:1] + ['-f', p, '-l', p] + cmd[1:]
    #~ print(cmd)
    subprocess.run(cmd, stdout=subprocess.PIPE)

def _export_pdf_to_jpg(pdf_path, dest, page=None):
    print('Convert PDF to JPG, please wait...')
    cmd = ['gs', '-dNOPAUSE', '-dBATCH', '-sDEVICE=jpeg', '-r200',
           '-sOutputFile=' + join(dest, 'p%03d.jpg'), pdf_path]
    if page is not None:
        cmd = cmd[:1] + ["-dFirstPage=%s" % page, "-dLastPage=%s" % page] + cmd[1:]
    subprocess.run(cmd, stdout=subprocess.PIPE)


def pdf2pic(*pdf_files, dest, page=None):
    "Clear `dest` folder, then extract all pages of the pdf files inside."
    rmtree(dest)
    mkdir(dest)
    tmp_dir = join(dest, '.tmp')
    for i, pdf in enumerate(pdf_files):
        print(f'Extracting all images from {basename(pdf)!r}, please wait...')
        rmtree(tmp_dir, ignore_errors=True)
        mkdir(tmp_dir)
        _extract_pictures(pdf, tmp_dir, page)
        # PDF may contain special files (OCR...) we can't handle.
        # In that case, we will rasterize pdf, using Ghostscript.
        pics = listdir(tmp_dir)
        if not all(any(f.endswith(ext) for ext in PIC_EXTS) for f in pics):
            rmtree(tmp_dir)
            mkdir(tmp_dir)
            _export_pdf_to_jpg(pdf, tmp_dir, page)
            pics = listdir(tmp_dir)
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
