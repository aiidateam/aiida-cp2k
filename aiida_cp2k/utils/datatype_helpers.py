###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""AiiDA-CP2K Gaussian Datatype Helpers."""

import re
from collections.abc import Sequence

import numpy as np
from aiida import common, engine, orm, plugins


def _unpack(adict):
    """Unpack any lists as values into single elements for the key"""

    for key, value in adict.items():
        if isinstance(value, Sequence):
            for item in value:
                yield (key, item)
        else:
            yield (key, value)


def _parse_name(label, default_type, sep=None):
    """
    Both BASIS_SET and POTENTIAL values can consist of either a single word or multiple ones,
    of which the first will be the type (if present).  Here we parse it and always return a tuple.
    """

    try:
        ltype, label = label.split(sep=sep, maxsplit=1)
    except ValueError:
        ltype = default_type

    return ltype, label


ELEMENT_MATCH = re.compile(r"(?P<sym>[a-z]{1,3})\d*", re.IGNORECASE)


def _kind_element_from_kind_section(section):
    """
    Get both kind and chemical symbol from a section, implementing
    the same auto-detection for chemical symbol/element from a KIND parameter
    as CP2K does.
    """
    try:
        kind = section["_"]
    except KeyError:
        raise common.InputValidationError(
            "No default parameter '_' found in KIND section."
        )

    try:
        element = section["ELEMENT"]
    except KeyError:
        # if there is no ELEMENT, CP2K automatically guesses it from the KIND, do the same
        match = ELEMENT_MATCH.match(kind)
        try:
            element = match["sym"]
        except TypeError:
            raise common.InputValidationError(
                f"Unable to figure out atomic symbol from KIND '{kind}'."
            )

    return kind, element


def _prepare_kind_section(inp, kind):
    """
    Insert a KIND section for a given 'StructureData.Kind'.
    Returns a reference to the newly created KIND section.
    """

    if "SUBSYS" not in inp["FORCE_EVAL"]:
        inp["FORCE_EVAL"]["SUBSYS"] = {}

    if "KIND" not in inp["FORCE_EVAL"]["SUBSYS"]:
        inp["FORCE_EVAL"]["SUBSYS"]["KIND"] = []

    inp["FORCE_EVAL"]["SUBSYS"]["KIND"].append(
        {
            "_": kind.name,
            "ELEMENT": kind.symbol,
        }
    )

    return inp["FORCE_EVAL"]["SUBSYS"]["KIND"][-1]


def _validate_gdt_namespace(entries, gdt_cls, attr):
    """Common namespace validator for both basissets and pseudos"""

    identifiers = []

    for kind, gdt_instance in _unpack(entries):
        if not isinstance(gdt_instance, gdt_cls):
            return f"invalid {attr} for '{kind}' specified"

        identifier = (gdt_instance.element, gdt_instance.name)

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

    with open(folder.get_abs_path(fname), mode="w", encoding="utf-8") as fhandle:
        for _, entry in _unpack(entries):
            entry.to_cp2k(fhandle)


def validate_basissets_namespace(basissets, _):
    """A input_namespace validator to ensure passed down basis sets have the correct type."""
    return _validate_gdt_namespace(
        basissets, plugins.DataFactory("gaussian.basisset"), "basis set"
    )


def validate_basissets(inp, basissets, structure):
    """
    Verify that all referenced basissets are present in the input.
    Currently supports 2 modes: either all of the basisssets are explicitly
    listed in a KIND section, or none of them are, at which point they're
    verified against the symbols in the structure.
    """

    # convert a structure
    #   {
    #      "ORB_O": [BasisSet<1>, BasisSet<2>],
    #      "AUX_O": BasisSet<3>,
    #      "H": BasisSet<4>,
    #   }
    # into
    #  [ ("ORB", "O", BasisSet<1>),
    #    ("ORB", "O", BasisSet<2>),
    #    ("AUX", "O", BasisSet<3>),
    #    ("ORB", "H", BasisSet<4>) ]
    # e.g. resolving any label to a (type,label) tuple, and unpack any list of basissets
    basissets = [
        (*_parse_name(label, default_type="ORB", sep="_"), bset)
        for label, bset in _unpack(basissets)
    ]
    basissets_specified = {bset for _, _, bset in basissets}
    basissets_used = set()
    explicit_kinds = []  # list of kinds with explicitly specified kind sections

    for section in (
        section
        for secpath, section in inp.param_iter(sections=True)
        if secpath[-1].upper() == "KIND"
    ):
        kind, element = _kind_element_from_kind_section(section)
        explicit_kinds += [kind]

        try:
            bsnames = section["BASIS_SET"]
        except KeyError:
            # if the BASIS_SET keyword is not present, try to look one up based on the given basissets
            bsets = [(t, b) for t, s, b in basissets if s == kind]

            # try again with lov.. with a chemical symbol
            if not bsets:
                bsets = [(t, b) for t, s, b in basissets if s == element]

            if not bsets:
                raise common.InputValidationError(
                    f"No basis set found for kind {kind} or element {element}"
                    f" in basissets input namespace and not explicitly set."
                )

            if len(bsets) > 1:
                section["BASIS_SET"] = [f"bstype {bset.name}" for bstype, bset in bsets]
            else:
                section["BASIS_SET"] = f"{bsets[0][0]} {bsets[0][1].name}"

            basissets_used.update(bset for _, bset in bsets)
        else:
            # The keyword BASIS_SET can occur multiple times, even for the same type, in which case
            # the specified basis sets are merged (given they match the same type)
            if isinstance(bsnames, str):
                bsnames = [_parse_name(bsnames, "ORB")]
            else:
                bsnames = [_parse_name(bsname, "ORB") for bsname in bsnames]

            for bstype, bsname in bsnames:
                bsets = [(t, b) for t, s, b in basissets if s == kind]

                # try again with a chemical symbol
                if not bsets:
                    bsets = [(t, b) for t, s, b in basissets if s == element]

                if not bsets:
                    raise common.InputValidationError(
                        f"'BASIS_SET {bstype} {bsname}' for element {element} (from kind {kind})"
                        " not found in basissets input namespace"
                    )

                for _, bset in bsets:
                    if bsname in bset.aliases:
                        basissets_used.add(bset)
                        break
                else:
                    raise common.InputValidationError(
                        f"'BASIS_SET {bstype} {bsname}' for element {element} (from kind {kind})"
                        " not found in basissets input namespace"
                    )

    # if there is no structure and there are any unreferenced basissets, end it here
    if not structure and any(
        bset not in basissets_used for bset in basissets_specified
    ):
        raise common.InputValidationError(
            "No explicit structure given and basis sets not referenced in input"
        )

    if isinstance(inp["FORCE_EVAL"], Sequence) and any(
        kind.name not in explicit_kinds for kind in structure.kinds
    ):
        raise common.InputValidationError(
            "Automated BASIS_SET keyword creation is not yet supported with multiple FORCE_EVALs."
            " Please explicitly reference a BASIS_SET for each KIND."
        )

    # check the structure against the present KIND sections and generate the missing ones
    for kind in structure.kinds:
        if kind.name in explicit_kinds:
            # nothing to do if the user already specified a KIND section for this KIND
            continue

        # the user can specify multiple types and even multiple basissets for the same KIND or ELEMENT
        # Try to find all of them by matching KIND name

        bsets = [(t, b) for t, s, b in basissets if s == kind.name]

        # if that returned none, try matching by chemical symbol/element again:
        if not bsets:
            bsets = [(t, b) for t, s, b in basissets if s == kind.symbol]

        if not bsets:
            raise common.InputValidationError(
                f"No basis set found in the given basissets for kind '{kind.name}' of your structure."
            )

        for _, bset in bsets:
            if bset.element != kind.symbol:
                raise common.InputValidationError(
                    f"Basis set '{bset.name}' for '{bset.element}' specified"
                    f" for kind '{kind.name}' (of '{kind.symbol}')."
                )

        kind_section = _prepare_kind_section(inp, kind)
        if len(bsets) > 1:
            kind_section["BASIS_SET"] = [
                f"{bstype} {bset.name}" for bstype, bset in bsets
            ]
        else:
            kind_section["BASIS_SET"] = f"{bsets[0][0]} {bsets[0][1].name}"

        explicit_kinds += [kind.name]
        basissets_used.update(bset for _, bset in bsets)

    for bset in basissets_specified:
        if bset not in basissets_used:
            raise common.InputValidationError(
                f"Basis set '{bset.name}' ('{bset.element}') specified in the basissets"
                f" input namespace but not referenced by either input or structure."
            )


def write_basissets(inp, basissets, folder):
    """Writes the unified BASIS_SETS file with the used basissets"""
    _write_gdt(inp, basissets, folder, "BASIS_SET_FILE_NAME", "BASIS_SETS")


def validate_pseudos_namespace(pseudos, _):
    """A input_namespace validator to ensure passed down pseudopentials have the correct type."""
    return _validate_gdt_namespace(
        pseudos, plugins.DataFactory("gaussian.pseudo"), "pseudo"
    )


def validate_pseudos(inp, pseudos, structure):
    """Verify that all referenced pseudos are present in the input"""

    pseudos_specified = {pseudo for _, pseudo in _unpack(pseudos)}
    pseudos_used = set()
    explicit_kinds = []  # list of kinds with explicitly specified kind sections

    for section in (
        section
        for secpath, section in inp.param_iter(sections=True)
        if secpath[-1].upper() == "KIND"
    ):
        kind, element = _kind_element_from_kind_section(section)
        explicit_kinds += [kind]

        try:
            pname = section["POTENTIAL"]
        except KeyError:
            # if the POTENTIAL keyword is not present, try to look one up based on given pseudos
            try:
                # first try with the KIND since this is the most specific one
                # NOTE: compared to basissets it doesn't make sense for the user to specify the type
                #       since the type of a pseudo can not be chosen (it is either an GTH, ECP, STO, etc.)
                pseudo = pseudos[kind]
            except KeyError:
                try:
                    pseudo = pseudos[element]
                except KeyError:
                    raise common.InputValidationError(
                        f"No pseudopotential found for kind {kind} or element {element}"
                        f" in pseudos input namespace and not explicitly set."
                    )

            # if the POTENTIAL keyword is missing completely, fill it up:
            section["POTENTIAL"] = f"GTH {pseudo.name}"
        else:
            ptype, pname = _parse_name(pname, "GTH")

            try:
                # first try with the KIND since this is the most specific one
                pseudo = pseudos[kind]
            except KeyError:
                try:
                    pseudo = pseudos[element]
                except KeyError:
                    raise common.InputValidationError(
                        f"'POTENTIAL {ptype} {pname}' for element {element} (from kind {kind})"
                        " not found in pseudos input namespace"
                    )

            if pname not in pseudo.aliases:
                raise common.InputValidationError(
                    f"'POTENTIAL {ptype} {pname}' for element {element} (from kind {kind})"
                    " not found in pseudos input namespace"
                )

        if pseudo.element != element:
            raise common.InputValidationError(
                f"Pseudopotential '{pseudo.name}' for '{pseudo.element}' specified"
                f" for element '{element}'."
            )

        pseudos_used.add(pseudo)

    # if there is no structure and there are any unreferenced pseudos, end it here
    if not structure and any(
        pseudo not in pseudos_used for pseudo in pseudos_specified
    ):
        raise common.InputValidationError(
            "No explicit structure given and pseudo not referenced in input"
        )

    if isinstance(inp["FORCE_EVAL"], Sequence) and any(
        kind.name not in explicit_kinds for kind in structure.kinds
    ):
        raise common.InputValidationError(
            "Automated POTENTIAL keyword creation is not yet supported with multiple FORCE_EVALs."
            " Please explicitly reference a POTENTIAL for each KIND."
        )

    # check the structure against the present KIND sections and generate the missing ones
    for kind in structure.kinds:
        if kind.name in explicit_kinds:
            # nothing to do if the user already specified a KIND section for this KIND
            continue

        try:
            pseudo = pseudos[kind.name]
        except KeyError:
            # if that returned none, try matching by chemical symbol/element again:
            try:
                pseudo = pseudos[kind.symbol]
            except KeyError:
                raise common.InputValidationError(
                    f"No basis set found in the given basissets"
                    f" for kind '{kind.name}' (or '{kind.symbol}') of your structure."
                )

        if pseudo.element != kind.symbol:
            raise common.InputValidationError(
                f"Pseudopotential '{pseudo.name}' for '{pseudo.element}' specified"
                f" for kind '{kind.name}' (of '{kind.symbol}')."
            )

        kind_section = _prepare_kind_section(inp, kind)
        kind_section["POTENTIAL"] = f"GTH {pseudo.name}"

        explicit_kinds += [kind.name]
        pseudos_used.add(pseudo)

    for pseudo in pseudos_specified:
        if pseudo not in pseudos_used:
            raise common.InputValidationError(
                f"Pseudopodential '{pseudo.name}' specified in the pseudos input namespace"
                f" but not referenced by either input or structure."
            )


def write_pseudos(inp, pseudos, folder):
    """Writes the unified POTENTIAL file with the used pseudos"""
    _write_gdt(inp, pseudos, folder, "POTENTIAL_FILE_NAME", "POTENTIAL")


def _merge_trajectories_into_dictionary(*trajectories, unique_stepids=False):
    if len(trajectories) < 0:
        return None
    final_trajectory_dict = {}

    array_names = trajectories[0].get_arraynames()

    for array_name in array_names:
        if any(array_name not in traj.get_arraynames() for traj in trajectories):
            raise ValueError(
                f"Array name '{array_name}' not found in all trajectories."
            )
        merged_array = np.concatenate(
            [traj.get_array(array_name) for traj in trajectories], axis=0
        )
        final_trajectory_dict[array_name] = merged_array

    # If unique_stepids is True, we only keep the unique stepids.
    # The other arrays are then also reduced to the unique stepids.
    if unique_stepids:
        stepids = np.concatenate([traj.get_stepids() for traj in trajectories], axis=0)
        final_trajectory_dict["stepids"], unique_indices = np.unique(
            stepids, return_index=True
        )

        for array_name in array_names:
            final_trajectory_dict[array_name] = final_trajectory_dict[array_name][
                unique_indices
            ]

    return final_trajectory_dict


def _dictionary_to_trajectory(trajectory_dict, symbols):
    final_trajectory = orm.TrajectoryData()
    final_trajectory.set_trajectory(
        symbols=symbols, positions=trajectory_dict.pop("positions")
    )
    for array_name, array in trajectory_dict.items():
        final_trajectory.set_array(array_name, array)

    return final_trajectory


@engine.calcfunction
def merge_trajectory_data_unique(*trajectories):
    trajectory_dict = _merge_trajectories_into_dictionary(
        *trajectories, unique_stepids=True
    )
    return _dictionary_to_trajectory(trajectory_dict, trajectories[0].symbols)


@engine.calcfunction
def merge_trajectory_data_non_unique(*trajectories):
    trajectory_dict = _merge_trajectories_into_dictionary(
        *trajectories, unique_stepids=False
    )
    return _dictionary_to_trajectory(trajectory_dict, trajectories[0].symbols)
