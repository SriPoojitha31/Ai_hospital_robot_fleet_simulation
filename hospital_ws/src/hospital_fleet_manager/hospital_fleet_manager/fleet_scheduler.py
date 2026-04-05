import time
import logging
from logging.handlers import TimedRotatingFileHandler

import rclpy
from rclpy.node import Node
from rclpy.executors import ExternalShutdownException
from std_msgs.msg import String
from scipy.optimize import linear_sum_assignment

from hospital_fleet_manager.hospital_map import build_hospital_map, shortest_path_length
from hospital_fleet_manager.ai_predictor import EnhancedAIPredictor


class FleetScheduler(Node):
    def __init__(self):
        super().__init__('fleet_scheduler')

        self.publisher = self.create_publisher(String, 'task_assignments', 10)

        self.hospital_map = build_hospital_map()
        self.predictor = EnhancedAIPredictor()

        # Setup file logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger('fleet_scheduler')
        handler = TimedRotatingFileHandler('/tmp/fleet_scheduler.log', when='midnight', interval=1, backupCount=7)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        self.robots = {
            'robot_1': 'Lobby',
            'robot_2': 'NurseStation',
            'robot_3': 'WardA',
            'robot_4': 'ER',
            'robot_5': 'Pharmacy',
        }

        self.tasks = [
            {'task_id': 'deliver_meds_1', 'from': 'Pharmacy', 'to': 'WardB'},
            {'task_id': 'pickup_samples_1', 'from': 'Lab', 'to': 'Radiology'},
            {'task_id': 'assist_patient_1', 'from': 'ER', 'to': 'ICU'},
            {'task_id': 'deliver_food_1', 'from': 'Cafeteria', 'to': 'WardA'},
            {'task_id': 'clean_room_1', 'from': 'NurseStation', 'to': 'WardB'},
            {'task_id': 'transport_equipment_1', 'from': 'Radiology', 'to': 'ICU'},
        ]

        self.get_logger().info('Fleet scheduler initialized with enhanced AI and periodic scheduling')
        self.logger.info('Fleet scheduler initialized with enhanced AI and periodic scheduling')

        # Periodic scheduling
        self.timer = self.create_timer(30.0, self.run_scheduler_cycle)  # Every 30 seconds

    def compute_cost_matrix(self):
        robot_names = list(self.robots.keys())
        tasks = self.tasks
        cost_matrix = []

        for robot in robot_names:
            robot_location = self.robots[robot]
            row = []
            for task in tasks:
                distance_to_pickup = shortest_path_length(self.hospital_map, robot_location, task['from'])
                distance_task = shortest_path_length(self.hospital_map, task['from'], task['to'])
                total_distance = distance_to_pickup + distance_task

                congestion = self.estimate_congestion(total_distance)
                predicted_time = self.predictor.predict(total_distance, congestion)
                row.append(predicted_time)

                self.get_logger().info(
                    f'Cost for {robot} -> {task["task_id"]}: distance={total_distance}, congestion={congestion}, predicted={predicted_time:.2f}'
                )
                self.logger.info(
                    f'Cost for {robot} -> {task["task_id"]}: distance={total_distance}, congestion={congestion}, predicted={predicted_time:.2f}'
                )

            cost_matrix.append(row)

        return robot_names, tasks, cost_matrix

    @staticmethod
    def estimate_congestion(distance):
        # simple congestion model: longer path = higher congestion index
        return max(0.0, distance - 2.0)

    def assign_tasks(self):
        robot_names, tasks, cost_matrix = self.compute_cost_matrix()

        if not cost_matrix:
            self.get_logger().warn('No tasks to assign')
            self.logger.warning('No tasks to assign')
            return []

        row_ind, col_ind = linear_sum_assignment(cost_matrix)

        assignments = []
        for r, t in zip(row_ind, col_ind):
            robot_name = robot_names[r]
            task_detail = tasks[t]
            assignment_msg = f'{robot_name}: {task_detail["task_id"]} ({task_detail["from"]} -> {task_detail["to"]})'
            assignments.append((robot_name, task_detail, assignment_msg))

        return assignments

    def publish_assignments(self, assignments):
        for robot_name, task_detail, assignment_msg in assignments:
            msg = String()
            msg.data = assignment_msg
            self.publisher.publish(msg)
            self.get_logger().info(f'Published assignment: {assignment_msg}')
            self.logger.info(f'Published assignment: {assignment_msg}')

    def update_robot_locations(self, assignments):
        for robot_name, task_detail, _ in assignments:
            self.robots[robot_name] = task_detail['to']

    def run_scheduler_cycle(self):
        self.get_logger().info('Starting scheduler cycle')
        self.logger.info('Starting scheduler cycle')
        assignments = self.assign_tasks()
        if not assignments:
            self.get_logger().warn('No assignments generated')
            self.logger.warning('No assignments generated')
            return

        self.publish_assignments(assignments)
        self.update_robot_locations(assignments)
        self.get_logger().info('Scheduler cycle completed')
        self.logger.info('Scheduler cycle completed')


def main(args=None):
    rclpy.init(args=args)
    node = FleetScheduler()
    node.get_logger().info('Fleet scheduler node started')
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
