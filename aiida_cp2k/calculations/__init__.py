###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""AiiDA-CP2K input plugin."""

import json
from operator import add

import numpy as np
from aiida.common import CalcInfo, CodeInfo, InputValidationError
from aiida.engine import CalcJob
from aiida.orm import Dict, RemoteData, SinglefileData
from aiida.plugins import DataFactory
from upf_to_json import upf_to_json

from ..utils import Cp2kInput
from ..utils.datatype_helpers import (
    validate_basissets,
    validate_basissets_namespace,
    validate_pseudos,
    validate_pseudos_namespace,
    write_basissets,
    write_pseudos,
)

BandsData = DataFactory("core.array.bands")
StructureData = DataFactory("core.structure")
TrajectoryData = DataFactory("core.array.trajectory")
KpointsData = DataFactory("core.array.kpoints")
UpfData = DataFactory("pseudo.upf")


class Cp2kCalculation(CalcJob):
    """This is a Cp2kCalculation, subclass of JobCalculation, to prepare input for an ab-initio CP2K calculation.

    For information on CP2K, refer to: https://www.cp2k.org.
    """

    # Defaults.
    _DEFAULT_INPUT_FILE = "aiida.inp"
    _DEFAULT_OUTPUT_FILE = "aiida.out"
    _DEFAULT_PROJECT_NAME = "aiida"
    _DEFAULT_RESTART_FILE_NAME = _DEFAULT_PROJECT_NAME + "-1.restart"
    _DEFAULT_TRAJECT_FILE_NAME = _DEFAULT_PROJECT_NAME + "-pos-1.dcd"
    _DEFAULT_TRAJECT_XYZ_FILE_NAME = _DEFAULT_PROJECT_NAME + "-pos-1.xyz"
    _DEFAULT_TRAJECT_FORCES_FILE_NAME = _DEFAULT_PROJECT_NAME + "-frc-1.xyz"
    _DEFAULT_TRAJECT_CELL_FILE_NAME = _DEFAULT_PROJECT_NAME + "-1.cell"
    _DEFAULT_PARENT_CALC_FLDR_NAME = "parent_calc/"
    _DEFAULT_COORDS_FILE_NAME = _DEFAULT_PROJECT_NAME + ".coords.xyz"
    _DEFAULT_INPUT_TRAJECT_XYZ_FILE_NAME = _DEFAULT_PROJECT_NAME + "-reftraj.xyz"
    _DEFAULT_INPUT_CELL_FILE_NAME = _DEFAULT_PROJECT_NAME + "-reftraj.cell"
    _DEFAULT_PARSER = "cp2k_base_parser"

    @classmethod
    def define(cls, spec):
        super().define(spec)

        # Input parameters.
        spec.input("parameters", valid_type=Dict, help="The input parameters.")
        spec.input(
            "structure",
            valid_type=StructureData,
            required=False,
            help="The main input structure.",
        )
        spec.input(
            "trajectory",
            valid_type=TrajectoryData,
            required=False,
            help="Input trajectory for a REFTRAJ simulation.",
        )
        spec.input(
            "settings",
            valid_type=Dict,
            required=False,
            help="Optional input parameters.",
        )
        spec.input(
            "parent_calc_folder",
            valid_type=RemoteData,
            required=False,
            help="Working directory of a previously ran calculation to restart from.",
        )
        spec.input(
            "kpoints", valid_type=KpointsData, required=False, help="Input kpoint mesh."
        )
        spec.input_namespace(
            "file",
            valid_type=(SinglefileData, StructureData),
            required=False,
            help="Additional input files.",
            dynamic=True,
        )

        spec.input_namespace(
            "basissets",
            dynamic=True,
            required=False,
            validator=validate_basissets_namespace,
            help=(
                "A dictionary of basissets to be used in the calculations: key is the atomic symbol,"
                " value is either a single basisset or a list of basissets. If multiple basissets for"
                " a single symbol are passed, it is mandatory to specify a KIND section with a BASIS_SET"
                " keyword matching the names (or aliases) of the basissets."
            ),
        )

        spec.input_namespace(
            "pseudos",
            dynamic=True,
            required=False,
            validator=validate_pseudos_namespace,
            help=(
                "A dictionary of pseudopotentials to be used in the calculations: key is the atomic symbol,"
                " value is either a single pseudopotential or a list of pseudopotentials. If multiple pseudos"
                " for a single symbol are passed, it is mandatory to specify a KIND section with a PSEUDOPOTENTIAL"
                " keyword matching the names (or aliases) of the pseudopotentials."
            ),
        )

        spec.input_namespace(
            "pseudos_upf",
            valid_type=UpfData,
            dynamic=True,
            required=True,
            help="A mapping of `UpfData` nodes onto the kind name to which they should apply.",
        )

        # Specify default parser.
        spec.input(
            "metadata.options.parser_name",
            valid_type=str,
            default=cls._DEFAULT_PARSER,
            non_db=True,
        )

        # Add input_filename attribute.
        spec.input(
            "metadata.options.input_filename",
            valid_type=str,
            default=cls._DEFAULT_INPUT_FILE,
        )

        # Add output_filename attribute.
        spec.input(
            "metadata.options.output_filename",
            valid_type=str,
            default=cls._DEFAULT_OUTPUT_FILE,
        )

        # Use mpi by default.
        spec.input("metadata.options.withmpi", valid_type=bool, default=True)

        # Unrecoverable errors: resources like the retrieved folder or its expected contents are missing.
        spec.exit_code(
            200,
            "ERROR_NO_RETRIEVED_FOLDER",
            message="The retrieved folder data node could not be accessed.",
        )
        spec.exit_code(
            210,
            "ERROR_OUTPUT_MISSING",
            message="The retrieved folder did not contain the required output file.",
        )

        # Unrecoverable errors: required retrieved files could not be read, parsed or are otherwise incomplete.
        spec.exit_code(
            301, "ERROR_OUTPUT_READ", message="The output file could not be read."
        )
        spec.exit_code(
            302, "ERROR_OUTPUT_PARSE", message="The output file could not be parsed."
        )
        spec.exit_code(
            303, "ERROR_OUTPUT_INCOMPLETE", message="The output file was incomplete."
        )
        spec.exit_code(
            304,
            "ERROR_OUTPUT_CONTAINS_ABORT",
            message='The output file contains the word "ABORT".',
        )
        spec.exit_code(
            312,
            "ERROR_STRUCTURE_PARSE",
            message="The output structure could not be parsed.",
        )
        spec.exit_code(
            321,
            "ERROR_COORDINATES_TRAJECTORY_READ",
            message="The coordinates trajectory file could not be read.",
        )

        spec.exit_code(
            323,
            "ERROR_FORCES_TRAJECTORY_READ",
            message="The forces trajectory file could not be read.",
        )

        spec.exit_code(
            325,
            "ERROR_CELLS_TRAJECTORY_READ",
            message="The cells trajectory file could not be read.",
        )

        spec.exit_code(
            350,
            "ERROR_UNEXPECTED_PARSER_EXCEPTION",
            message="The parser raised an unexpected exception.",
        )

        # Significant errors but calculation can be used to restart.
        spec.exit_code(
            400,
            "ERROR_OUT_OF_WALLTIME",
            message="The calculation stopped prematurely because it ran out of walltime.",
        )
        spec.exit_code(
            450,
            "ERROR_SCF_NOT_CONVERGED",
            message="SCF cycle did not converge for the given threshold.",
        )
        spec.exit_code(
            500,
            "ERROR_GEOMETRY_CONVERGENCE_NOT_REACHED",
            message="The ionic minimization cycle did not converge for the given thresholds.",
        )
        spec.exit_code(
            501,
            "ERROR_MAXIMUM_NUMBER_OPTIMIZATION_STEPS_REACHED",
            message="The maximum number of optimization steps reached.",
        )

        # Output parameters.
        spec.output(
            "output_parameters",
            valid_type=Dict,
            required=True,
            help="The output dictionary containing results of the calculation.",
        )
        spec.output(
            "output_structure",
            valid_type=StructureData,
            required=False,
            help="The relaxed output structure.",
        )
        spec.output(
            "output_trajectory",
            valid_type=TrajectoryData,
            required=False,
            help="The output trajectory.",
        )
        spec.output(
            "output_bands",
            valid_type=BandsData,
            required=False,
            help="Computed electronic band structure.",
        )
        spec.default_output_node = "output_parameters"

        spec.outputs.dynamic = True

    def prepare_for_submission(self, folder):
        """Create the input files from the input nodes passed to this instance of the `CalcJob`.

        :param folder: an `aiida.common.folders.Folder` to temporarily write files on disk
        :return: `aiida.common.datastructures.CalcInfo` instance
        """

        # Create cp2k input file.
        inp = Cp2kInput(self.inputs.parameters.get_dict())
        inp.add_keyword("GLOBAL/PROJECT", self._DEFAULT_PROJECT_NAME)

        # Create input structure(s).
        if "structure" in self.inputs:
            # As far as I understand self.inputs.structure can't deal with tags
            # self.inputs.structure.export(folder.get_abs_path(self._DEFAULT_COORDS_FILE_NAME), fileformat="xyz")
            self._write_structure(
                self.inputs.structure, folder, self._DEFAULT_COORDS_FILE_NAME
            )

            # modify the input dictionary accordingly
            for i, letter in enumerate("ABC"):
                inp.add_keyword(
                    "FORCE_EVAL/SUBSYS/CELL/" + letter,
                    "{:<15} {:<15} {:<15}".format(*self.inputs.structure.cell[i]),
                    override=False,
                    conflicting_keys=["ABC", "ALPHA_BETA_GAMMA", "CELL_FILE_NAME"],
                )

            topo = "FORCE_EVAL/SUBSYS/TOPOLOGY"
            inp.add_keyword(
                topo + "/COORD_FILE_NAME",
                self._DEFAULT_COORDS_FILE_NAME,
                override=False,
            )
            inp.add_keyword(
                topo + "/COORD_FILE_FORMAT",
                "XYZ",
                override=False,
                conflicting_keys=["COORDINATE"],
            )

        # Create input trajectory files
        if "trajectory" in self.inputs:
            self._write_trajectories(
                self.inputs.trajectory,
                folder,
                self._DEFAULT_INPUT_TRAJECT_XYZ_FILE_NAME,
                self._DEFAULT_INPUT_CELL_FILE_NAME,
            )

        if "basissets" in self.inputs:
            validate_basissets(
                inp,
                self.inputs.basissets,
                self.inputs.structure if "structure" in self.inputs else None,
            )
            write_basissets(inp, self.inputs.basissets, folder)

        if "pseudos" in self.inputs:
            validate_pseudos(
                inp,
                self.inputs.pseudos,
                self.inputs.structure if "structure" in self.inputs else None,
            )
            write_pseudos(inp, self.inputs.pseudos, folder)

        if "pseudos_upf" in self.inputs:
            for atom_kind, pseudo in self.inputs.pseudos_upf.items():
                pseudo_dict = upf_to_json(pseudo.get_content(), atom_kind)
                with folder.open(atom_kind + ".json", "w") as fobj:
                    fobj.write(json.dumps(pseudo_dict, indent=2))

        # Kpoints.
        if "kpoints" in self.inputs:
            try:
                mesh, _ = self.inputs.kpoints.get_kpoints_mesh()
            except AttributeError:
                raise InputValidationError(
                    "K-point sampling for SCF must be given in mesh form."
                )

            inp.add_keyword(
                "FORCE_EVAL/DFT/KPOINTS",
                {
                    "SCHEME": f"MONKHORST-PACK {mesh[0]} {mesh[1]} {mesh[2]}",
                    "EPS_GEO": "1.0E-8",
                    "FULL_GRID": "OFF",
                    "SYMMETRY": "OFF",
                },
            )

        with open(
            folder.get_abs_path(self._DEFAULT_INPUT_FILE), mode="w", encoding="utf-8"
        ) as fobj:
            try:
                fobj.write(inp.render())
            except ValueError as exc:
                raise InputValidationError(
                    "Invalid keys or values in input parameters found"
                ) from exc

        settings = self.inputs.settings.get_dict() if "settings" in self.inputs else {}

        # Create code info.
        codeinfo = CodeInfo()
        codeinfo.cmdline_params = settings.pop("cmdline", []) + [
            "-i",
            self._DEFAULT_INPUT_FILE,
        ]
        codeinfo.stdout_name = self._DEFAULT_OUTPUT_FILE
        codeinfo.join_files = True
        codeinfo.code_uuid = self.inputs.code.uuid

        # Create calc info.
        calcinfo = CalcInfo()
        calcinfo.uuid = self.uuid
        calcinfo.cmdline_params = codeinfo.cmdline_params
        calcinfo.stdin_name = self._DEFAULT_INPUT_FILE
        calcinfo.stdout_name = self._DEFAULT_OUTPUT_FILE
        calcinfo.codes_info = [codeinfo]

        # Files or additional structures.
        if "file" in self.inputs:
            calcinfo.local_copy_list = []
            for name, obj in self.inputs.file.items():
                if isinstance(obj, SinglefileData):
                    calcinfo.local_copy_list.append(
                        (obj.uuid, obj.filename, obj.filename)
                    )
                elif isinstance(obj, StructureData):
                    self._write_structure(obj, folder, name + ".xyz")

        calcinfo.retrieve_list = [
            self._DEFAULT_OUTPUT_FILE,
            self._DEFAULT_RESTART_FILE_NAME,
            self._DEFAULT_TRAJECT_FILE_NAME,
            self._DEFAULT_TRAJECT_XYZ_FILE_NAME,
            self._DEFAULT_TRAJECT_FORCES_FILE_NAME,
            self._DEFAULT_TRAJECT_CELL_FILE_NAME,
        ]
        calcinfo.retrieve_list += settings.pop("additional_retrieve_list", [])

        # Symlinks.
        calcinfo.remote_symlink_list = []
        calcinfo.remote_copy_list = []
        if "parent_calc_folder" in self.inputs:
            comp_uuid = self.inputs.parent_calc_folder.computer.uuid
            remote_path = self.inputs.parent_calc_folder.get_remote_path()
            copy_info = (comp_uuid, remote_path, self._DEFAULT_PARENT_CALC_FLDR_NAME)

            # If running on the same computer - make a symlink.
            if self.inputs.code.computer.uuid == comp_uuid:
                calcinfo.remote_symlink_list.append(copy_info)
            # If not - copy the folder.
            else:
                calcinfo.remote_copy_list.append(copy_info)

        # Check for left over settings.
        if settings:
            raise InputValidationError(
                f"The following keys have been found in the settings input node {self.pk}, but were not understood: "
                + ",".join(settings.keys())
            )

        return calcinfo

    @staticmethod
    def _write_structure(structure, folder, name):
        """Function that writes a structure and takes care of element tags."""

        xyz = _atoms_to_xyz(structure.get_ase())
        with open(folder.get_abs_path(name), mode="w", encoding="utf-8") as fobj:
            fobj.write(xyz)

    @staticmethod
    def _write_trajectories(trajectory, folder, name_pos, name_cell):
        """Function that writes a structure and takes care of element tags."""

        (xyz, cell) = _trajectory_to_xyz_and_cell(trajectory)
        with open(folder.get_abs_path(name_pos), mode="w", encoding="utf-8") as fobj:
            fobj.write(xyz)
        if cell is not None:
            with open(
                folder.get_abs_path(name_cell), mode="w", encoding="utf-8"
            ) as fobj:
                fobj.write(cell)


def kind_names(atoms):
    """Get atom kind names from ASE atoms based on tags.

    Simply append the tag to element symbol. E.g., 'H' with tag 1 becomes 'H1'.
    Note: This mirrors the behavior of StructureData.get_kind_names()

    :param atoms: ASE atoms instance
    :returns: list of kind names
    """
    elem_tags = ["" if t == 0 else str(t) for t in atoms.get_tags()]
    return list(map(add, atoms.get_chemical_symbols(), elem_tags))


def _atoms_to_xyz(atoms, infoline="No info"):
    """Converts ASE atoms to string, taking care of element tags.

    :param atoms: ASE Atoms instance
    :returns: str (in xyz format)
    """
    elem_symbols = kind_names(atoms)
    elem_coords = [
        f"{p[0]:25.16f} {p[1]:25.16f} {p[2]:25.16f}" for p in atoms.get_positions()
    ]
    xyz = f"{len(elem_coords)}\n"
    xyz += f"{infoline}\n"
    xyz += "\n".join(map(add, elem_symbols, elem_coords))
    return xyz


def _trajectory_to_xyz_and_cell(trajectory):
    """Converts postions and cell from a TrajectoryData  to string, taking care of element tags from ASE atoms.

    :param atoms: ASE Atoms instance
    :param trajectory: TrajectoryData instance
    :returns: positions str (in xyz format) and cell str
    """
    cell = None
    xyz = ""
    stepids = trajectory.get_stepids()
    for i, step in enumerate(stepids):
        xyz += _atoms_to_xyz(
            trajectory.get_step_structure(i).get_ase(),
            infoline=f"i = {step+1} , time = {(step+1)*0.5}",  # reftraj trajectories cannot start from STEP 0
        )
        xyz += "\n"
    if "cells" in trajectory.get_arraynames():
        cell = "#   Step   Time [fs]       Ax [Angstrom]       Ay [Angstrom]       Az [Angstrom]       Bx [Angstrom]       By [Angstrom]       Bz [Angstrom]       Cx [Angstrom]       Cy [Angstrom]       Cz [Angstrom]      Volume [Angstrom^3]\n"
        cell_vecs = [
            f"{stepid+1} {(stepid+1)*0.5:6.3f} {cellvec[0][0]:25.16f} {cellvec[0][1]:25.16f} {cellvec[0][2]:25.16f} {cellvec[1][0]:25.16f} {cellvec[1][1]:25.16f} {cellvec[1][2]:25.16f} {cellvec[2][0]:25.16f} {cellvec[2][1]:25.16f} {cellvec[2][2]:25.16f} {np.dot(cellvec[0], np.cross(cellvec[1], cellvec[2]))}"
            for (stepid, cellvec) in zip(stepids, trajectory.get_array("cells"))
        ]
        cell += "\n".join(cell_vecs)
    return xyz, cell
