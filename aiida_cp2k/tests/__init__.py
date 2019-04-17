""" tests for the plugin
Use the aiida.utils.fixtures.PluginTestCase class for convenient
testing that does not pollute your profiles/databases.
"""

# Helper functions for tests
from __future__ import absolute_import
from __future__ import print_function

import os
import tempfile


TEST_DIR = os.path.dirname(os.path.realpath(__file__))
TEST_COMPUTER = "localhost-test"

EXECUTABLES = {"cp2k": "cp2k"}


def get_path_to_executable(executable):
    """ Get path to local executable.
    :param executable: Name of executable in the $PATH variable
    :type executable: str
    :return: path to executable
    :rtype: str
    """
    # pylint issue https://github.com/PyCQA/pylint/issues/73
    import distutils.spawn  # pylint: disable=no-name-in-module,import-error

    path = distutils.spawn.find_executable(executable)
    if path is None:
        raise ValueError("{} executable not found in PATH.".format(executable))

    return path


def get_computer(name=TEST_COMPUTER, workdir=None):
    """Get AiiDA computer.
    Loads computer 'name' from the database, if exists.
    Sets up local computer 'name', if it isn't found in the DB.

    :param name: Name of computer to load or set up.
    :param workdir: path to work directory
        Used only when creating a new computer.
    :return: The computer node
    :rtype: :py:class:`aiida.orm.Computer`
    """
    from aiida.orm import Computer
    from aiida.common.exceptions import NotExistent

    try:
        computer = Computer.objects.get(name=name)
    except NotExistent:
        if workdir is None:
            workdir = tempfile.mkdtemp()

        computer = Computer(
            name=name,
            description="localhost computer set up by aiida_diff tests",
            hostname=name,
            workdir=workdir,
            transport_type="local",
            scheduler_type="direct",
        )
        computer.store()
        computer.configure()

    return computer


def get_code(entry_point, computer=None):
    """Get local code.
    Sets up code for given entry point on given computer.

    :param entry_point: Entry point of calculation plugin
    :param computer_name: Name of (local) computer
    :return: The code node
    :rtype: :py:class:`aiida.orm.Code`
    """
    from aiida.orm import Code
    from aiida.common.exceptions import NotExistent

    try:
        executable = EXECUTABLES[entry_point]
    except KeyError:
        raise KeyError(
            "Entry point {} not recognized. Allowed values: {}".format(
                entry_point, list(EXECUTABLES.keys())
            )
        )

    if computer is None:
        computer = get_computer()

    try:
        code = Code.get_from_string("{}@{}".format(executable, computer.get_name()))
    except NotExistent:
        path = get_path_to_executable(executable)
        code = Code(
            input_plugin_name=entry_point, remote_computer_exec=[computer, path]
        )
        code.label = executable
        code.store()

    return code
