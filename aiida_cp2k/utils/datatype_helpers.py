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
            return f"invalid {attr} for '{kind}' specified"

        identifier = _identifier(gdt_instance)

        if identifier in identifiers:
            # note: this should be possible for basissets with different versions
            #       but at this point we should require some format for the key to match it
            return f"{attr} for kind {gdt_instance.element} ({gdt_instance.name}) specified multiple times"

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


def validate_basissets(inp, basissets, structure):
    """
    Verify that all referenced basissets are present in the input.
    Currently supports 2 modes: either all of the basisssets are explicitly
    listed in a KIND section, or none of them are, at which point they're
    verified against the symbols in the structure.
    """
    # pylint: disable=too-many-branches

    basisset_used = {_identifier(bset): 0 for _, bset in _unpack(basissets)}
    basisset_kw_used = False

    for secpath, section in inp.param_iter(sections=True):
        # ignore non-kind sections
        if secpath[-1].upper() != "KIND":
            continue

        if "BASIS_SET" not in section:
            # ignore kind sections without a BASIS_SET keyword
            continue

        basisset_kw_used = True

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
                raise InputValidationError(f"'BASIS_SET {bstype} {bsname}' for element {element} (from kind {kind})"
                                           " not found in basissets input namespace")

    if basisset_kw_used:
        for (sym, name), used in basisset_used.items():
            if not used:
                raise InputValidationError(f"Basis sets provided in calculation for kind {sym} ({name}),"
                                           " but not used in input")
        # if all basissets are referenced in the input, we're done
        return

    if not structure:  # no support for COORD section (yet)
        raise InputValidationError("No explicit structure given and basis sets not referenced in input")

    if isinstance(inp["FORCE_EVAL"], Sequence):
        raise InputValidationError(
            "Automated BASIS_SET keyword creation is not yet supported with multiple FORCE_EVALs."
            " Please explicitly reference a BASIS_SET for each KIND.")

    allowed_labels = structure.get_kind_names() + list(structure.get_symbols_set())

    for label, bset in _unpack(basissets):
        try:
            label, bstype = label.split("_", maxsplit=1)
        except ValueError:
            bstype = "ORB"

        if label not in allowed_labels:
            raise InputValidationError(f"Basis sets provided in calculation for kind {bset.element} ({bset.name}),"
                                       f" with label {label} could not be matched to a kind in the structure")

        if "SUBSYS" not in inp["FORCE_EVAL"]:
            inp["FORCE_EVAL"]["SUBSYS"] = {}

        if "KIND" not in inp["FORCE_EVAL"]["SUBSYS"]:
            inp["FORCE_EVAL"]["SUBSYS"]["KIND"] = []

        kind_sec = next((s for s in inp["FORCE_EVAL"]["SUBSYS"]["KIND"] if s.get("_", "") == label), None)

        if not kind_sec:
            inp["FORCE_EVAL"]["SUBSYS"]["KIND"].append({"_": label})
            kind_sec = inp["FORCE_EVAL"]["SUBSYS"]["KIND"][-1]

        kind_sec["BASIS_SET"] = f"{bstype} {bset.name}"
        if "ELEMENT" not in kind_sec:
            kind_sec["ELEMENT"] = bset.element


def estimate_added_mos(basissets, structure, fraction=0.3):
    """Calculate an estimate for ADDED_MOS based on used basis sets"""

    symbols = [structure.get_kind(s.kind_name).get_symbols_string() for s in structure.sites]
    n_mos = 0

    # We are currently overcounting in the following cases:
    #   * if we get a mix of ORB basissets for the same chemical symbol but different sites
    #   * if we get multiple basissets for one element (merged within CP2K)

    for label, bset in _unpack(basissets):
        try:
            _, bstype = label.split("_", maxsplit=1)
        except ValueError:
            bstype = "ORB"

        if bstype != "ORB":  # ignore non-ORB basissets
            continue

        n_mos += symbols.count(bset.element) * bset.n_orbital_functions

    # at least one additional MO per site, otherwise a fraction of the total number of orbital functions
    return max(len(symbols), int(fraction * n_mos))


def write_basissets(inp, basissets, folder):
    """Writes the unified BASIS_SETS file with the used basissets"""
    _write_gdt(inp, basissets, folder, "BASIS_SET_FILE_NAME", "BASIS_SETS")


def validate_pseudos_namespace(pseudos, _):
    """A input_namespace validator to ensure passed down pseudopentials have the correct type."""
    return _validate_gdt_namespace(pseudos, DataFactory("gaussian.pseudo"), "pseudo")


def validate_pseudos(inp, pseudos, structure):
    """Verify that all referenced pseudos are present in the input"""

    # pylint: disable=too-many-branches

    # there can be only one pseudo per kind, thus, no _unpack
    pseudo_used = {_identifier(pseudo): 0 for _, pseudo in pseudos.items()}
    pseudo_kw_used = False

    for secpath, section in inp.param_iter(sections=True):
        # ignore non-kind sections
        if secpath[-1].upper() != "KIND":
            continue

        kind = section["_"]
        element = section.get("ELEMENT", kind)

        pname = section.get("POTENTIAL", section.get("POT"))

        if pname is None:
            # ignore kind sections without a POTENTIAL keyword (or POT alias)
            continue

        try:
            ptype, pname = pname.split(maxsplit=1)
        except ValueError:
            ptype = "GTH"

        pseudo_kw_used = True

        try:
            pseudo_used[(element, pname)] += 1
        except KeyError:
            raise InputValidationError(f"'POTENTIAL {ptype} {pname}' for element {element} (from kind {kind})"
                                       " not found in pseudos input namespace")

    if pseudo_kw_used:
        for (sym, name), used in pseudo_used.items():
            if not used:
                raise InputValidationError(f"Pseudos provided in calculation for kind {sym} ({name}),"
                                           " but not used in input")
        return

    if not structure:  # no support for COORD section (yet)
        raise InputValidationError("No explicit structure given and pseudos not referenced in input")

    if isinstance(inp["FORCE_EVAL"], Sequence):
        raise InputValidationError(
            "Automated POTENTIAL keyword creation is not yet supported with multiple FORCE_EVALs."
            " Please explicitly reference a POTENTIAL for each KIND.")

    allowed_labels = structure.get_kind_names() + list(structure.get_symbols_set())

    for label, pseudo in pseudos.items():
        if label not in allowed_labels:
            raise InputValidationError(f"Pseudo provided in calculation for kind {pseudo.element} ({pseudo.name}),"
                                       f" with label {label} could not be matched to a kind in the structure")

        if "SUBSYS" not in inp["FORCE_EVAL"]:
            inp["FORCE_EVAL"]["SUBSYS"] = {}

        if "KIND" not in inp["FORCE_EVAL"]["SUBSYS"]:
            inp["FORCE_EVAL"]["SUBSYS"]["KIND"] = []

        kind_sec = next((s for s in inp["FORCE_EVAL"]["SUBSYS"]["KIND"] if s.get("_", "") == label), None)

        if not kind_sec:
            inp["FORCE_EVAL"]["SUBSYS"]["KIND"].append({"_": label})
            kind_sec = inp["FORCE_EVAL"]["SUBSYS"]["KIND"][-1]

        kind_sec["POTENTIAL"] = f"GTH {pseudo.name}"

        if "ELEMENT" not in kind_sec:
            kind_sec["ELEMENT"] = pseudo.element


def write_pseudos(inp, pseudos, folder):
    """Writes the unified POTENTIAL file with the used pseudos"""
    _write_gdt(inp, pseudos, folder, "POTENTIAL_FILE_NAME", "POTENTIAL")
