import pytest
from unittest.mock import MagicMock, patch
import os
import rclpy

from hospital_fleet_manager.fleet_scheduler import FleetScheduler


@pytest.fixture(scope="session", autouse=True)
def init_rclpy():
    ros_log_dir = "/tmp/ai_hospital_ros_logs"
    os.makedirs(ros_log_dir, exist_ok=True)
    os.environ.setdefault("ROS_LOG_DIR", ros_log_dir)
    if not rclpy.ok():
        rclpy.init()
    yield
    if rclpy.ok():
        rclpy.shutdown()


@pytest.fixture
def scheduler():
    with patch('hospital_fleet_manager.fleet_scheduler.EnhancedAIPredictor') as MockPredictor, \
         patch('hospital_fleet_manager.fleet_scheduler.shortest_path_length', return_value=1), \
         patch('hospital_fleet_manager.fleet_scheduler.shortest_path', return_value=['A', 'B']):
        mock_predictor = MagicMock()
        mock_predictor.predict = lambda d, c: 1.0
        MockPredictor.return_value = mock_predictor

        s = FleetScheduler()
        s.hospital_map = MagicMock()
        yield s
        s.destroy_node()


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
