import pytest

import azwebapps.main
from azwebapps.cmd import read_tests

testdata = read_tests()


@pytest.mark.parametrize("args,now,expected", testdata)
def test_recorded(args, now, expected):
    if expected is None:
        assert azwebapps.main.main(args, now) is None
    else:
        assert expected == azwebapps.main.main(args, now)
