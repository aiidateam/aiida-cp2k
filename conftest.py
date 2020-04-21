"""
For pytest initialise a test database and profile
"""
import pytest
pytest_plugins = ['aiida.manage.tests.pytest_fixtures']  # pylint: disable=invalid-name


@pytest.fixture(scope='function')
def cp2k_code(aiida_local_code_factory):  # pylint: disable=unused-argument
    return aiida_local_code_factory("cp2k", "cp2k")


@pytest.fixture(scope='function')
def clear_database(aiida_profile):
    """Clear the database after a test with this fixture"""
    yield
    aiida_profile.reset_db()
