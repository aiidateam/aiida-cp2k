import numpy as np
import pytest
from aiida import orm

from aiida_cp2k.utils import merge_trajectory_data


@pytest.mark.parametrize(
    "step_ranges",
    (
        [(1, 20), (21, 40)],
        [(1, 20), (15, 30)],
        [(1, 20), (21, 40), (41, 60)],
        [(1, 25), (21, 30), (31, 60), (45, 80)],
    ),
)
def test_merge_trajectory_data(step_ranges):
    def get_trajectory(step1=1, step2=20):
        nstes = step2 - step1 + 1
        positions = np.array(
            [
                [[2, 2, 2.73 + 0.05 * np.random.random()], [2, 2, 2]]
                for i in range(nstes)
            ]
        )
        cells = np.array(
            [
                [[4, 0, 0], [0, 4, 0], [0, 0, 4.75 + 0.05 * np.random.random()]]
                for i in range(nstes)
            ]
        )
        stepids = np.arange(step1, step2 + 1)
        symbols = ["H", "H"]
        trajectory = orm.TrajectoryData()
        trajectory.set_trajectory(symbols, positions, cells=cells, stepids=stepids)
        return trajectory

    trajectories = [get_trajectory(*step_range) for step_range in step_ranges]

    total_length = sum(
        [step_range[1] - step_range[0] + 1 for step_range in step_ranges]
    )

    unique_elements = []
    for step_range in step_ranges:
        unique_elements.extend(range(step_range[0], step_range[1] + 1))
    total_lenght_unique = len(set(unique_elements))

    merged_trajectory = merge_trajectory_data(*trajectories)
    assert (
        len(merged_trajectory.get_stepids()) == total_length
    ), "The merged trajectory has the wrong length."

    merged_trajectory_unique = merge_trajectory_data(*trajectories, unique_stepids=True)
    assert (
        len(merged_trajectory_unique.get_stepids()) == total_lenght_unique
    ), "The merged trajectory with unique stepids has the wrong length."
