import pytest

from auto_backup.config import ConfigValueInjector


class ClassForInjectionTest(object):
    def __init__(self, water, milk):
        self.water = water
        self.milk = milk


def function_for_injection_test(water, milk="default"):
    return water, milk


@pytest.fixture
def config():
    return {"water": "value-for-water", "milk": 1}


@pytest.fixture
def function_injector():
    return ConfigValueInjector(function_for_injection_test)


@pytest.fixture
def class_injector():
    return ConfigValueInjector(ClassForInjectionTest)


def test_inject_into_function(function_injector, config):
    injected_values = function_injector.build(config)

    assert injected_values == ("value-for-water", 1)


def test_inject_into_class_init(class_injector, config):
    instance = class_injector.build(config)

    assert (instance.water, instance.milk) == ("value-for-water", 1)


def test_provided_value_overrides_config(class_injector, config):
    instance = class_injector.provide_values(water="provided").build(config)

    assert instance.water, instance.milk == ("provided", 1)


def test_default_value_is_used_when_not_in_config(function_injector, config):
    del config["milk"]
    injected_values = function_injector.build(config)

    assert injected_values == ("value-for-water", "default")


def test_injects_none_if_no_other_value_present(function_injector, config):
    del config["water"]
    injected_values = function_injector.build(config)

    assert injected_values == (None, 1)
