""" tests for the plugin

Use the aiida.utils.fixtures.PluginTestCase class for convenient
testing that does not pollute your profiles/databases.
"""

import os
import tempfile


TEST_DIR = os.path.dirname(os.path.realpath(__file__))
TEST_COMPUTER = 'localhost-test'

executables = {
    'cp2k': 'cp2k',
}


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

    from aiida.common.exceptions import NotExistent

    from aiida.orm import Computer

    try:
        computer = Computer.objects.get(name=name)
    except NotExistent:
        if workdir is None:
            workdir = tempfile.mkdtemp()

        computer = Computer(
            name=name,
            description='localhost computer set up by aiida_cp2k tests',
            hostname=name,
            workdir=workdir,
            transport_type='local',
            scheduler_type='direct',
            enabled_state=True)

        computer.store()

    # TODO configure computer for user, see
    # aiida_core.aiida.cmdline.commands.computer.Computer.computer_configure

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
        executable = executables[entry_point]
    except KeyError:
        raise KeyError(
            "Entry point {} not recognized. Allowed values: {}".format(
                entry_point, list(executables.keys())))

    if computer is None:
        computer = get_computer()

    try:
        code = Code.get_from_string('{}@{}'.format(executable,
                                                   computer.get_name()))
    except NotExistent:
        path = get_path_to_executable(executable)
        code = Code(
            input_plugin_name=entry_point,
            remote_computer_exec=[computer, path],
        )
        code.label = executable
        code.store()

    return code


def calculation_execution_test(calc, allowed_returncodes=(0, ), check_paths=None):
    """ test that a calculation executes successfully

    :param calc: the calculation
    :param allowed_returncodes: raise RunTimeError if return code is not in allowed_returncodes
    :param check_paths: raise OSError if these relative paths are not in the folder after execution
    :return:
    """
    # pylint: disable=too-many-locals
    from aiida.common.folders import SandboxFolder
    import stat
    import subprocess

    # output input files and scripts to temporary folder
    with SandboxFolder() as folder:

        subfolder, script_filename = calc.submit_test(folder=folder)
        print("inputs created at {}".format(subfolder.abspath))

        script_path = os.path.join(subfolder.abspath, script_filename)
        scheduler_stderr = calc._SCHED_ERROR_FILE  # pylint: disable=protected-access

        # we first need to make sure the script is executable
        st = os.stat(script_path)
        os.chmod(script_path, st.st_mode | stat.S_IEXEC)
        # now call script, NB: bash -l -c is required to access global variable loaded in .bash_profile
        returncode = subprocess.call(["bash", "-l", "-c", script_path], cwd=subfolder.abspath)

        if returncode not in allowed_returncodes:
            err_msg = "process failed (and couldn't find stderr file: {})".format(scheduler_stderr)
            stderr_path = os.path.join(subfolder.abspath, scheduler_stderr)
            if os.path.exists(stderr_path):
                with open(stderr_path) as f:
                    err_msg = "Process failed with stderr:\n{}".format(f.read())
            raise RuntimeError(err_msg)

        if check_paths is not None:
            for outpath in check_paths:
                subfolder.get_abs_path(outpath, check_existence=True)

        print("calculation completed execution")
