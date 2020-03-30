"""
For pytest initialise a test database and profile
"""
from __future__ import absolute_import
import pytest
pytest_plugins = ['aiida.manage.tests.pytest_fixtures']  # pylint: disable=invalid-name


@pytest.fixture(scope='function')
def cp2k_code(aiida_local_code_factory):  # pylint: disable=unused-argument
    return aiida_local_code_factory("cp2k", "cp2k.popt")
