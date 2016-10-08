"""
AUTOmcq

This extension enables computer corrected tests.

An example:

    <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

    ======= Mathematics ===========

    * 1+1 =
    - 1
    + 2
    - 3
    - 4

    - an other answer

    ======= Litterature ==========

    * "to be or not to be", but who actually wrote that ?
    + W. Shakespeare
    - I. Newton
    - W. Churchill
    - Queen Victoria
    - Some bloody idiot

    * Jean de la Fontaine was a famous french
    - pop singer
    - dancer
    + writer
    - detective
    - cheese maker

    -> his son is also famous for
    -  dancing french cancan
    - conquering Honolulu
    - walking for the first time on the moon
    - having breafkeast at Tiffany

    + none of the above is correct

    >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>


One may include some PTYX code of course.

#NEW INT(2,10) a, b, c, d WITH a*b - c*d != 0


    """

import re
from generate import generate_tex

def main(text):

    code, cfg = generate_tex(text)

    with open('/tmp/ptyx-autoqcm.log', 'w') as f:
        f.write(code)
    return code, cfg


