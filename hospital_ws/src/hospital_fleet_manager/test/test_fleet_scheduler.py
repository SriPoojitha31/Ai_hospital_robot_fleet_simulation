import pytest
from unittest.mock import MagicMock, patch

from hospital_fleet_manager.fleet_scheduler import FleetScheduler


@pytest.fixture
def scheduler():
    with patch('hospital_fleet_manager.fleet_scheduler.EnhancedAIPredictor') as MockPredictor, \
         patch('hospital_fleet_manager.fleet_scheduler.shortest_path_length', return_value=1):
        mock_predictor = MagicMock()
        mock_predictor.predict = lambda d, c: 1.0
        MockPredictor.return_value = mock_predictor

        s = FleetScheduler()
        s.hospital_map = MagicMock()
        return s


def test_compute_cost_matrix(scheduler):
    robot_names, tasks, cost_matrix = scheduler.compute_cost_matrix()
    assert len(cost_matrix) == len(robot_names)
    assert len(cost_matrix[0]) == len(tasks)


def test_assign_tasks(scheduler):
    assignments = scheduler.assign_tasks()
    assert isinstance(assignments, list)


def test_estimate_congestion():
    assert FleetScheduler.estimate_congestion(1) == 0.0
    assert FleetScheduler.estimate_congestion(3) == 1.0
