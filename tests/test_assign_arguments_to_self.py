from unittest.mock import MagicMock

import pytest

from auto_backup.argument_assigner import assign_arguments_to_self


class AssignArgumentsMock(object):
    def __init__(self, water, earth="brown", *, wind, fire="purple"):
        assign_arguments_to_self()

    def values(self):
        return self.water, self.earth, self.wind, self.fire


def assign_argument_function(self, a, b):
    assign_arguments_to_self()


def no_self_function(a, b):
    assign_arguments_to_self()


def test_assigns_all_provided_arguments():
    instance = AssignArgumentsMock("blue", "red", wind="green", fire="yellow")

    assert instance.values() == ("blue", "red", "green", "yellow")


def test_default_argument_gets_assigned():
    instance = AssignArgumentsMock("blue", wind="pink")

    assert instance.values() == ("blue", "brown", "pink", "purple")


def test_raises_an_exception_when_there_is_no_self_argument():
    with pytest.raises(KeyError):
        no_self_function(1, 2)


def test_assign_to_self_argument_of_arbitrary_function():
    mock = MagicMock()

    assign_argument_function(mock, "avalue", "bvalue")

    assert (mock.a, mock.b) == ("avalue", "bvalue")
