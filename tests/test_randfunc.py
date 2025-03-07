from ptyx.randfunc import randchoice, srandchoice, randfrac


def test_randchoice():
    for i in range(1000):
        assert randchoice(0, 1, exclude=[0]) == 1
        assert srandchoice(0, 1, exclude=[0, 1]) == -1
        assert randchoice([0, 1, 2], exclude=[0]) in [1, 2]
        assert srandchoice([0, 1, 2], exclude=[0, 1]) in [-1, -2, 2]


def test_randfrac():
    for i in range(1000):
        assert randfrac(2, 7, den=6).q == 6
