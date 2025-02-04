"""For pytest initialise a test database and profile."""

import subprocess

import pytest

pytest_plugins = ["aiida.manage.tests.pytest_fixtures"]


@pytest.fixture(scope="function")
def cp2k_code(aiida_local_code_factory):
    return aiida_local_code_factory(
        entry_point="cp2k",
        executable="/opt/conda/envs/cp2k/bin/cp2k.psmp",
        prepend_text='eval "$(command conda shell.bash hook 2> /dev/null)"\nconda activate cp2k\n',
    )


# from https://stackoverflow.com/a/25188424
# required for examples for optional features to show appropriate error messages
def pytest_configure(config):
    import sys

    sys._called_from_test = True


def pytest_unconfigure(config):
    import sys

    del sys._called_from_test


@pytest.fixture(scope="session", autouse=True)
def setup_sssp_pseudos(aiida_profile):
    """Create an SSSP pseudo potential family from scratch."""
    subprocess.run(
        [
            "aiida-pseudo",
            "install",
            "sssp",
            "-p",
            "efficiency",
            "-x",
            "PBE",
            "-v",
            "1.3",
        ]
    )
