# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""AiiDA-CP2K Gaussian Datatype Helpers."""

import io
from collections.abc import Sequence

from aiida.common import InputValidationError
from aiida.plugins import DataFactory


def _unpack(adict):
    """Unpack any lists as values into single elements for the key"""

    for key, value in adict.items():
        if isinstance(value, Sequence):
            for item in value:
                yield (key, item)
        else:
            yield (key, value)


def _identifier(bset):
    """Our uniquenes identifier for basis sets"""
    return bset.element, bset.name


def validate_basissets_namespace(basissets, _):
    """A input_namespace validator to ensure passed down basis sets have the correct type."""

    BasisSet = DataFactory("gaussian.basisset")  # pylint: disable=invalid-name

    identifiers = []

    for kind, bset in _unpack(basissets):
        if not isinstance(bset, BasisSet):
            return "invalid basis set for '{kind}' specified".format(kind=kind)

        identifier = _identifier(bset)

        if identifier in identifiers:
            # note: this should be possible for basissets with different versions
            #       but at this point we should require some format for the key to match it
            return "basis set for kind {bset.element} ({bset.name}) specified multiple times".format(bset=bset)

        identifiers += [identifier]

    return None


def validate_basissets(inp, basissets):
    """Verify that all referenced basissets are present in the input"""

    basisset_used = {_identifier(bset): 0 for _, bset in _unpack(basissets)}

    for secpath, section in inp.param_iter(sections=True):
        # ignore non-kind sections
        if secpath[-1].upper() != "KIND":
            continue

        if "BASIS_SET" not in section:
            # ignore kind sections without a BASIS_SET keyword
            continue

        kind = section["_"]
        element = section.get("ELEMENT", kind)

        # the BASIS_SET keyword can be repeated, even for the same type
        bsnames = section["BASIS_SET"]

        # the keyword BASIS_SET can occur multiple times in which case
        # the specified basis sets are merged (given they match the same type)
        if isinstance(bsnames, str):
            bsnames = [bsnames]

        for bsname in bsnames:
            # test for new-style basis set specification
            try:
                bstype, bsname = bsname.split(maxsplit=1)
            except ValueError:
                bstype = "ORB"

            try:
                basisset_used[(element, bsname)] += 1
            except KeyError:
                raise InputValidationError(("'BASIS_SET {bstype} {bsname}' for element {element} (from kind {kind})"
                                            " not found in basissets input namespace").format(bsname=bsname,
                                                                                              bstype=bstype,
                                                                                              element=element,
                                                                                              kind=kind))

    for (sym, name), used in basisset_used.items():
        if not used:
            raise InputValidationError("Basis sets provided in calculation for kind {sym} ({name}),"
                                       " but not used in input".format(sym=sym, name=name))


def write_basissets(inp, basissets, folder):
    """Writes the unified BASIS_SETS file with the used basissets"""

    # inject BASIS_SET_FILE_NAME into all FORCE_EVAL/DFT sections
    for secpath, section in inp.param_iter(sections=True):
        if secpath[-1].upper() == "DFT":
            section["BASIS_SET_FILE_NAME"] = "BASIS_SETS"

    with io.open(folder.get_abs_path("BASIS_SETS"), mode="w", encoding="utf-8") as fhandle:
        for _, bset in _unpack(basissets):
            bset.to_cp2k(fhandle)
