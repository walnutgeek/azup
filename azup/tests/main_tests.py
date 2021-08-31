import pytest

from azup.cmd import read_tests
from azup.tests.main import t_main

testdata = read_tests()


@pytest.mark.parametrize("args,now,expected", testdata)
def test_recorded(args, now, expected):
    if expected is None:
        assert t_main(args, now) is None
    else:
        assert expected == t_main(args, now)
