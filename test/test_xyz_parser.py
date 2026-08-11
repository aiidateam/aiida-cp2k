###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""Test parsing CP2K XYZ trajectories."""

import pytest

from aiida_cp2k.utils.xyz import parse

CP2K_XYZ = """\
2
 i = 0, time = 0.000, E = -1.2500000000E+01
 C1  0.0  1.0  2.0
 H2 -0.35 +4.0 5.
2
 i = 1, time = 0.500, E = -1.3000000000E+01
 C1  0.1  1.1  2.1
 H2 -0.4  4.1  5.1
"""


def test_parse_cp2k_xyz():
    """Parse CP2K frames with kind labels and signed coordinates."""

    frames = parse(CP2K_XYZ)

    assert frames == [
        {
            "natoms": 2,
            "comment": " i = 0, time = 0.000, E = -1.2500000000E+01",
            "atoms": [("C1", (0.0, 1.0, 2.0)), ("H2", (-0.35, 4.0, 5.0))],
        },
        {
            "natoms": 2,
            "comment": " i = 1, time = 0.500, E = -1.3000000000E+01",
            "atoms": [("C1", (0.1, 1.1, 2.1)), ("H2", (-0.4, 4.1, 5.1))],
        },
    ]


def test_parse_cp2k_xyz_bytes():
    """Preserve the upstream byte-input behavior."""

    frames = parse(CP2K_XYZ.encode())

    assert frames[0]["comment"] == " i = 0, time = 0.000, E = -1.2500000000E+01"
    assert frames[0]["atoms"][0][0] == b"C1"


def test_parse_cp2k_xyz_file_handles(tmp_path):
    """Parse text and binary file handles identically."""

    xyz_file = tmp_path / "trajectory.xyz"
    xyz_file.write_text(CP2K_XYZ)

    with xyz_file.open() as handle:
        text_frames = parse(handle)
    with xyz_file.open("rb") as handle:
        binary_frames = parse(handle)

    assert text_frames == binary_frames
    assert text_frames[0]["atoms"][0][0] == b"C1"


def test_parse_preserves_restart_frames():
    """Do not silently remove repeated step IDs produced by a restart."""

    restarted = CP2K_XYZ + CP2K_XYZ.replace("i = 0", "i = 1", 1)

    frames = parse(restarted)

    assert len(frames) == 4
    assert [frame["comment"].split(",")[0].strip() for frame in frames] == [
        "i = 0",
        "i = 1",
        "i = 1",
        "i = 1",
    ]


def test_parse_rejects_too_few_atoms():
    """Reject frames with fewer atom records than declared."""

    content = """\
2
incomplete frame
H 0.0 0.0 0.0
"""

    with pytest.raises(ValueError, match="1 is smaller than the number of atoms 2"):
        parse(content)


def test_parse_rejects_too_many_atoms():
    """Reject frames with more atom records than declared."""

    content = """\
1
overfull frame
H 0.0 0.0 0.0
H 1.0 1.0 1.0
"""

    with pytest.raises(TypeError, match="2 is larger than the number of atoms 1"):
        parse(content)
