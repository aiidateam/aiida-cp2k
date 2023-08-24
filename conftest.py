"""For pytest initialise a test database and profile."""
import pytest

pytest_plugins = ["aiida.manage.tests.pytest_fixtures"]


@pytest.fixture(scope="function")
def cp2k_code(aiida_local_code_factory):
    return aiida_local_code_factory("cp2k", "cp2k")


@pytest.fixture(scope="function", autouse=True)
def clear_database(aiida_profile_clean):
    """Automatically clear database in between tests."""


# from https://stackoverflow.com/a/25188424
# required for examples for optional features to show appropriate error messages
def pytest_configure(config):
    import sys

    sys._called_from_test = True


def pytest_unconfigure(config):
    import sys

    del sys._called_from_test
