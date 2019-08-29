#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Aug 29 14:49:37 2019

@author: nicolas
"""
from os.path import join
from PIL import Image, ImageDraw, ImageFont
from numpy import int8

from square_detection import COLORS

def _correct_checkboxes(draw, pos, checked, correct, size):
    j, i = pos
    margin = size//2
    red = COLORS['red']
    green = COLORS['green']
    # Draw a blue square around the box (for debuging purpose).
    draw.rectangle((i, j, i+size, j+size), outline=green)
    if checked and not correct:
        # Circle checkbox with red pen.
        draw.ellipse((i-margin, j-margin, i+size+margin, j+size+margin), outline=red)
    elif not checked and correct:
        # Check (cross) the box (with red pen).
        draw.line((i, j, i+size, j+size), fill=red)
        draw.line((i+size, j, i, j+size), fill=red)


def _write_score(draw, pos, earn, size):
    j, i = pos
    red = COLORS['red']
    fnt = ImageFont.truetype('FreeSerif.ttf', int(0.7*size))
    if int(earn) == earn:
        earn = int(earn)
    draw.text((i - 2*size, j), str(earn), font=fnt, fill=red)


def amend_all(data, config, save_dir):
    """Amend answer sheet with scores and correct answers.

    `data` is the dict generated when the answer sheet is scanned.
    `ID` is the ID of answer sheet.
    """
    for ID, d in data.items():
        pics = {}
        for page, page_data in d['pages'].items():
            top_left_positions = {}
            # Convert to RGB picture.
#            pic = Image.open(page_data['file']).convert('RGB')
            array = page_data['matrix']
            pic = Image.fromarray((255*array).astype(int8)).convert('RGB')
            # Drawing context
            draw = ImageDraw.Draw(pic)
            size = page_data['cell_size']
            for (q, a), pos in page_data['positions'].items():
                checked = (a in page_data['answered'][q])
                correct = (a in config['correct_answers'][q])
                _correct_checkboxes(draw, pos, checked, correct, size)
                if q in top_left_positions:
                    i0, j0 = top_left_positions[q]
                    i, j = pos
                    top_left_positions[q] = (min(i, i0), min(j, j0))
                else:
                    top_left_positions[q] = pos
            for q in top_left_positions:
                print(q, top_left_positions[q], d['score_per_question'][q])
                earn = d['score_per_question'][q]
                _write_score(draw, top_left_positions[q], earn, size)
            # We will now sort pages.
            # For that, we use questions numbers: the page which displays
            # the smaller questions numbers is the first one, and so on.
            # However, be carefull to use displayed questions numbers,
            # since `q` is the question number *before shuffling*.
            q_num = page_data['questions_nums'][q]
            pics[q_num] = pic
            # Sort pages now.
            _, pages = zip(*sorted(pics.items()))
        pages[0].save(join(save_dir, f"{d['name']}-{ID}.pdf"), save_all=True,
                 append_images=pages[1:])

