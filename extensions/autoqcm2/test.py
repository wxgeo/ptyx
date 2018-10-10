from importlib import reload

import _tests

def test():
    #~ reload(_tests)
    _tests.test1()
    _tests.test2()

if __name__ == '__main__':
    test()
    print("\n*** All tests pass ! ***")

