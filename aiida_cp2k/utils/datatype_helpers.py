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


def _identifier(gdt):
    """Our unique identifier for gaussian datatypes"""
    return gdt.element, gdt.name


def _validate_gdt_namespace(entries, gdt_cls, attr):
    """Common namespace validator for both basissets and pseudos"""

    identifiers = []

    for kind, gdt_instance in _unpack(entries):
        if not isinstance(gdt_instance, gdt_cls):
            return "invalid {attr} for '{kind}' specified".format(attr=attr, kind=kind)

        identifier = _identifier(gdt_instance)

        if identifier in identifiers:
            # note: this should be possible for basissets with different versions
            #       but at this point we should require some format for the key to match it
            return "{attr} for kind {gdt_instance.element} ({gdt_instance.name}) specified multiple times".format(
                attr=attr, gdt_instance=gdt_instance)

        identifiers += [identifier]

    return None


def _write_gdt(inp, entries, folder, key, fname):
    """inject <key>=<fname> into all FORCE_EVAL/DFT sections and write the entries to a file"""

    for secpath, section in inp.param_iter(sections=True):
        if secpath[-1].upper() == "DFT":
            section[key] = fname

    with io.open(folder.get_abs_path(fname), mode="w", encoding="utf-8") as fhandle:
        for _, entry in _unpack(entries):
            entry.to_cp2k(fhandle)


def validate_basissets_namespace(basissets, _):
    """A input_namespace validator to ensure passed down basis sets have the correct type."""
    return _validate_gdt_namespace(basissets, DataFactory("gaussian.basisset"), "basis set")


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
    _write_gdt(inp, basissets, folder, "BASIS_SET_FILE_NAME", "BASIS_SETS")


def validate_pseudos_namespace(pseudos, _):
    """A input_namespace validator to ensure passed down pseudopentials have the correct type."""
    return _validate_gdt_namespace(pseudos, DataFactory("gaussian.pseudo"), "pseudo")


def validate_pseudos(inp, pseudos):
    """Verify that all referenced pseudos are present in the input"""

    pseudo_used = {_identifier(pseudo): 0 for _, pseudo in _unpack(pseudos)}

    for secpath, section in inp.param_iter(sections=True):
        # ignore non-kind sections
        if secpath[-1].upper() != "KIND":
            continue

        kind = section["_"]
        element = section.get("ELEMENT", kind)

        try:
            pname = section.get("POTENTIAL", section["POT"])
        except KeyError:
            # ignore kind sections without a POTENTIAL keyword (or POT alias)
            continue

        try:
            pseudo_used[(element, pname)] += 1
        except KeyError:
            raise InputValidationError(("'POTENTIAL {pname}' for element {element} (from kind {kind})"
                                        " not found in pseudos input namespace").format(pname=pname,
                                                                                        element=element,
                                                                                        kind=kind))

    for (sym, name), used in pseudo_used.items():
        if not used:
            raise InputValidationError("Pseudos provided in calculation for kind {sym} ({name}),"
                                       " but not used in input".format(sym=sym, name=name))


def write_pseudos(inp, pseudos, folder):
    """Writes the unified POTENTIAL file with the used pseudos"""
    _write_gdt(inp, pseudos, folder, "POTENTIAL_FILE_NAME", "POTENTIAL")
