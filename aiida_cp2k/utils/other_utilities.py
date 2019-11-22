# -*- coding: utf-8 -*-
"""Other utilities."""
from __future__ import absolute_import
from collections import namedtuple

from aiida.common import AiidaException, AttributeDict
from aiida.engine import ExitCode
from aiida.orm import Dict


class UnexpectedCalculationFailure(AiidaException):
    """Raised when a calculation job has failed for an unexpected or unrecognized reason."""


ErrorHandlerReport = namedtuple('ErrorHandlerReport', 'is_handled do_break exit_code')
ErrorHandlerReport.__new__.__defaults__ = (False, False, ExitCode())
"""
A namedtuple to define an error handler report for a :class:`~aiida.engine.processes.workchains.workchain.WorkChain`.
This namedtuple should be returned by an error handling method of a workchain instance if
the condition of the error handling was met by the failure mode of the calculation.
If the error was appriopriately handled, the 'is_handled' field should be set to `True`,
and `False` otherwise. If no further error handling should be performed after this method
the 'do_break' field should be set to `True`
:param is_handled: boolean, set to `True` when an error was handled, default is `False`
:param do_break: boolean, set to `True` if no further error handling should be performed, default is `False`
:param exit_code: an instance of the :class:`~aiida.engine.processes.exit_code.ExitCode` tuple
"""


def prepare_process_inputs(process, inputs):
    """Prepare the inputs for submission for the given process, according to its spec.

    That is to say that when an input is found in the inputs that corresponds to an input port in the spec of the
    process that expects a `Dict`, yet the value in the inputs is a plain dictionary, the value will be wrapped in by
    the `Dict` class to create a valid input.

    :param process: sub class of `Process` for which to prepare the inputs dictionary
    :param inputs: a dictionary of inputs intended for submission of the process
    :return: a dictionary with all bare dictionaries wrapped in `Dict` if dictated by the process spec
    """
    prepared_inputs = wrap_bare_dict_inputs(process.spec().inputs, inputs)
    return AttributeDict(prepared_inputs)


def wrap_bare_dict_inputs(port_namespace, inputs):
    """Wrap bare dictionaries in `inputs` in a `Dict` node if dictated by the corresponding port in given namespace.

    :param port_namespace: a `PortNamespace`
    :param inputs: a dictionary of inputs intended for submission of the process
    :return: a dictionary with all bare dictionaries wrapped in `Dict` if dictated by the port namespace
    """
    from aiida.engine.processes import PortNamespace

    wrapped = {}

    for key, value in inputs.items():

        if key not in port_namespace:
            wrapped[key] = value
            continue

        port = port_namespace[key]

        if isinstance(port, PortNamespace):
            wrapped[key] = wrap_bare_dict_inputs(port, value)
        elif port.valid_type == Dict and isinstance(value, dict):
            wrapped[key] = Dict(dict=value)
        else:
            wrapped[key] = value

    return wrapped
