"""For pytest initialise a test database and profile."""

import pytest
import requests
from aiida_pseudo.cli.install import install_sssp

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
def setup_sssp_pseudos(aiida_profile, tmp_path_factory):
    """Install the same SSSP 1.3 data through the current Archive API.

    The aiida-pseudo versions compatible with legacy AiiDA releases use the
    retired Materials Cloud download endpoint. Download the files explicitly
    and retain aiida-pseudo's checksum and cutoff validation during installation.
    """
    directory = tmp_path_factory.mktemp("sssp")
    record_url = "https://archive.materialscloud.org/api/records/rcyfm-68h65"
    paths = []
    for extension in ("tar.gz", "json"):
        filename = f"SSSP_1.3.0_PBE_efficiency.{extension}"
        response = requests.get(f"{record_url}/files/{filename}/content", timeout=120)
        response.raise_for_status()
        path = directory / filename
        path.write_bytes(response.content)
        paths.append(path)
    install_sssp(*paths, label="SSSP/1.3/PBE/efficiency")
