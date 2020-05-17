#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Aug 29 14:49:37 2019

@author: nicolas
"""
from os.path import join
from PIL import Image, ImageDraw, ImageFont

from .square_detection import COLORS


def _correct_checkboxes(draw, pos, checked, correct, size):
    i, j = pos
    margin = size//2
    red = COLORS['red']
    green = COLORS['green']
    # Draw a blue square around the box (for debuging purpose).
    draw.rectangle((j, i, j+size, i+size), outline=green)
    if checked and not correct:
        # Circle checkbox with red pen.
        try:
            draw.ellipse((j-margin, i-margin, j+size+margin, i+size+margin),
                         width=2, outline=red)
        except TypeError:
            # old PIL versions (<5.1.3)
            draw.ellipse((j-margin, i-margin, j+size+margin, i+size+margin),
                         outline=red)
    elif not checked and correct:
        # Check (cross) the box (with red pen).
        draw.line((j, i, j+size-1, i+size-1), fill=red, width=2)
        draw.line((j+size-1, i, j, i+size-1), fill=red, width=2)


def _write_score(draw, pos, earn, size):
    i, j = pos
    red = COLORS['red']
    fnt = ImageFont.truetype('FreeSerif.ttf', int(0.7*size))
    if isinstance(earn, float):
        earn = f"{earn:g}"
    draw.text((j, i), earn, font=fnt, fill=red)


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
            pic = Image.open(page_data['webp']).convert('RGB')
            if not page_data['positions']:
                # The last page of the MCQ may be empty.
                # `float('+inf')` is used to ensure
                # it will be the last page when sorting.
                pics[float('+inf')] = pic
                continue
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
                earn = d['score_per_question'][q]
                i, j = top_left_positions[q]
                _write_score(draw, (i, j - 2*size), earn, size)
            # We will now sort pages.
            # For that, we use questions numbers: the page which displays
            # the smaller questions numbers is the first one, and so on.
            # However, be carefull to use displayed questions numbers,
            # since `q` is the question number *before shuffling*.
            q_num = page_data['questions_nums'][q]
            pics[q_num] = pic
            # Sort pages now.
        _, pages = zip(*sorted(pics.items()))
        draw = ImageDraw.Draw(pages[0])
        _write_score(draw, (2*size, 4*size), f"{d['score']:g}/{config['max_score']:g}", 2*size)
        pages[0].save(join(save_dir, f"{d['name']}-{ID}.pdf"), save_all=True,
                 append_images=pages[1:])

