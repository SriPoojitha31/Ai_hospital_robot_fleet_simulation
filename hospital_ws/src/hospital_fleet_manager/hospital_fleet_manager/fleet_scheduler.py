import time
import logging
import random
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

        # Diverse robot fleet with specializations
        self.robots = {
            'delivery_1': {'location': 'MainLobby', 'type': 'delivery', 'battery': 100.0},
            'delivery_2': {'location': 'Pharmacy', 'type': 'delivery', 'battery': 100.0},
            'delivery_3': {'location': 'ER', 'type': 'delivery', 'battery': 100.0},
            'cleaning_1': {'location': 'WardA', 'type': 'cleaning', 'battery': 100.0},
            'cleaning_2': {'location': 'ICU', 'type': 'cleaning', 'battery': 100.0},
            'patient_mover_1': {'location': 'ER', 'type': 'patient_mover', 'battery': 100.0},
            'patient_mover_2': {'location': 'Recovery', 'type': 'patient_mover', 'battery': 100.0},
            'heavy_supply_1': {'location': 'Supply', 'type': 'heavy_supply', 'battery': 100.0},
            'lab_courier_1': {'location': 'Lab', 'type': 'lab_courier', 'battery': 100.0},
            'emergency_1': {'location': 'ER', 'type': 'emergency_response', 'battery': 100.0},
            'general_1': {'location': 'MainLobby', 'type': 'general', 'battery': 100.0},
            'general_2': {'location': 'Cafeteria', 'type': 'general', 'battery': 100.0},
        }

        self.tasks = [
            # Medication delivery (high-priority)
            {'task_id': 'med_delivery_1', 'from': 'Pharmacy', 'to': 'WardB', 'priority': 'high', 'type': 'delivery', 'duration': 8},
            {'task_id': 'med_delivery_2', 'from': 'Pharmacy', 'to': 'ICU', 'priority': 'critical', 'type': 'delivery', 'duration': 10},
            # Cleaning tasks
            {'task_id': 'clean_ward_a', 'from': 'WardA', 'to': 'WardA', 'priority': 'medium', 'type': 'cleaning', 'duration': 20},
            {'task_id': 'clean_er', 'from': 'ER', 'to': 'ER', 'priority': 'high', 'type': 'cleaning', 'duration': 15},
            # Patient transport (critical)
            {'task_id': 'patient_move_1', 'from': 'ER', 'to': 'ICU', 'priority': 'critical', 'type': 'patient_mover', 'duration': 12},
            {'task_id': 'patient_move_2', 'from': 'Trauma', 'to': 'Recovery', 'priority': 'critical', 'type': 'patient_mover', 'duration': 15},
            # Lab work
            {'task_id': 'lab_samples_1', 'from': 'Lab', 'to': 'Radiology', 'priority': 'high', 'type': 'lab_courier', 'duration': 8},
            {'task_id': 'lab_samples_2', 'from': 'Lab', 'to': 'ER', 'priority': 'critical', 'type': 'lab_courier', 'duration': 6},
            # Supply delivery
            {'task_id': 'supply_stock_1', 'from': 'Supply', 'to': 'Pharmacy', 'priority': 'medium', 'type': 'heavy_supply', 'duration': 12},
            {'task_id': 'supply_stock_2', 'from': 'Supply', 'to': 'OperatingRoom1', 'priority': 'high', 'type': 'heavy_supply', 'duration': 10},
            # Equipment
            {'task_id': 'equip_move_1', 'from': 'Radiology', 'to': 'ICU', 'priority': 'medium', 'type': 'heavy_supply', 'duration': 14},
            # Food/cafeteria
            {'task_id': 'food_delivery_1', 'from': 'Cafeteria', 'to': 'WardA', 'priority': 'low', 'type': 'delivery', 'duration': 10},
            {'task_id': 'food_delivery_2', 'from': 'Cafeteria', 'to': 'Recovery', 'priority': 'medium', 'type': 'delivery', 'duration': 10},
            # Document/report delivery
            {'task_id': 'document_delivery_1', 'from': 'Administration', 'to': 'ER', 'priority': 'low', 'type': 'delivery', 'duration': 5},
        ]

        self.get_logger().info('Fleet scheduler initialized with enhanced AI and periodic scheduling')
        self.logger.info('Fleet scheduler initialized with enhanced AI and periodic scheduling')

        # Periodic scheduling
        self.timer = self.create_timer(30.0, self.run_scheduler_cycle)  # Every 30 seconds
        
        # Task tracking
        self.assignment_history = []
        self.task_counter = 0
        
    def generate_dynamic_tasks(self):
        """Generate new tasks based on hospital patterns."""
        new_tasks = []
        task_types_by_specialty = {
            'delivery': [
                {'from_pool': ['Pharmacy', 'Supply'], 'to_pool': ['WardA', 'WardB', 'WardC', 'WardD', 'WardE', 'ICU']},
            ],
            'cleaning': [
                {'from_pool': ['WardA', 'WardB', 'WardC', 'WardD', 'WardE', 'ER'], 'to_pool': ['WardA', 'WardB', 'WardC', 'WardD', 'WardE', 'ER']},
            ],
            'patient_mover': [
                {'from_pool': ['ER', 'Trauma'], 'to_pool': ['ICU', 'PICU', 'Recovery', 'WardA', 'WardB']},
            ],
            'lab_courier': [
                {'from_pool': ['Lab'], 'to_pool': ['Radiology', 'ER', 'ICU', 'OperatingRoom1']},
            ],
            'heavy_supply': [
                {'from_pool': ['Supply', 'Sterilization'], 'to_pool': ['OperatingRoom1', 'OperatingRoom2', 'ER', 'ICU']},
            ],
        }
        
        priorities = ['critical', 'high', 'medium', 'low']
        priority_weights = [0.1, 0.3, 0.4, 0.2]  # Higher chance of medium/low in random generation
        
        # Generate 1-3 new tasks randomly
        num_new_tasks = random.randint(1, 3)
        for _ in range(num_new_tasks):
            if random.random() < 0.6:  # 60% chance to add a task
                specialty = random.choice(list(task_types_by_specialty.keys()))
                route = random.choice(task_types_by_specialty[specialty])
                from_loc = random.choice(route['from_pool'])
                to_loc = random.choice(route['to_pool'])
                priority = random.choices(priorities, weights=priority_weights)[0]
                self.task_counter += 1
                
                task = {
                    'task_id': f'{specialty}_task_{self.task_counter}',
                    'from': from_loc,
                    'to': to_loc,
                    'priority': priority,
                    'type': specialty,
                    'duration': random.randint(5, 20),
                    'generated': True,  # Mark as dynamically generated
                }
                new_tasks.append(task)
        
        return new_tasks

    def compute_cost_matrix(self):
        robot_names = list(self.robots.keys())
        tasks = self.tasks
        cost_matrix = []

        # Specialization compatibility rules
        specialty_match_bonus = {
            'delivery': ['delivery', 'general'],
            'cleaning': ['cleaning', 'general'],
            'patient_mover': ['patient_mover', 'emergency_response', 'general'],
            'lab_courier': ['lab_courier', 'delivery', 'general'],
            'heavy_supply': ['heavy_supply', 'general'],
            'emergency_response': ['emergency_response', 'patient_mover', 'general'],
        }
        
        # Priority penalty multipliers (higher = more penalized)
        priority_weights = {
            'critical': 0.5,   # Avoid robots with low battery for critical tasks
            'high': 0.7,
            'medium': 0.9,
            'low': 1.0,
        }

        for robot in robot_names:
            robot_info = self.robots[robot]
            robot_location = robot_info['location']
            robot_type = robot_info['type']
            robot_battery = robot_info['battery']
            
            row = []
            for task in tasks:
                # Base distance cost
                distance_to_pickup = shortest_path_length(self.hospital_map, robot_location, task['from'])
                distance_task = shortest_path_length(self.hospital_map, task['from'], task['to'])
                total_distance = distance_to_pickup + distance_task

                congestion = self.estimate_congestion(total_distance)
                predicted_time = self.predictor.predict(total_distance, congestion)
                
                # Specialization matching bonus (reduce cost for matched specialties)
                spec_bonus = 0.0
                if task['type'] in specialty_match_bonus.get(robot_type, ['general']):
                    spec_bonus = -2.0  # Reduce cost for matched specialty
                
                # Battery penalty for critical tasks
                battery_penalty = 0.0
                if robot_battery < 30.0 and task['priority'] == 'critical':
                    battery_penalty = 50.0  # Large penalty for low battery on critical tasks
                elif robot_battery < 50.0 and task['priority'] == 'high':
                    battery_penalty = 15.0
                
                # Priority weight (make cost relative to priority)
                priority_weight = priority_weights.get(task['priority'], 1.0)
                
                # Total cost
                cost = (predicted_time * priority_weight) + spec_bonus + battery_penalty
                
                row.append(cost)

                self.get_logger().info(
                    f'Cost for {robot}(type={robot_type}) -> {task["task_id"]}(priority={task["priority"]}): '
                    f'distance={total_distance}, time={predicted_time:.2f}, spec_bonus={spec_bonus:.2f}, '
                    f'battery_penalty={battery_penalty:.2f}, total={cost:.2f}'
                )
                self.logger.info(
                    f'Cost for {robot}(type={robot_type}) -> {task["task_id"]}(priority={task["priority"]}): '
                    f'distance={total_distance}, time={predicted_time:.2f}, spec_bonus={spec_bonus:.2f}, '
                    f'battery_penalty={battery_penalty:.2f}, total={cost:.2f}'
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
            self.robots[robot_name]['location'] = task_detail['to']
            # Simulate battery drain: ~2-3% per task
            self.robots[robot_name]['battery'] = max(0.0, self.robots[robot_name]['battery'] - random.uniform(2.0, 3.0))

    def run_scheduler_cycle(self):
        self.get_logger().info('Starting scheduler cycle')
        self.logger.info('Starting scheduler cycle')
        
        # Generate new dynamic tasks
        new_tasks = self.generate_dynamic_tasks()
        self.tasks.extend(new_tasks)
        if new_tasks:
            self.get_logger().info(f'Generated {len(new_tasks)} new tasks')
            self.logger.info(f'Generated {len(new_tasks)} new tasks')
        
        # Clean up completed/old tasks (keep only last 30)
        if len(self.tasks) > 30:
            self.tasks = self.tasks[-30:]
        
        assignments = self.assign_tasks()
        if not assignments:
            self.get_logger().warn('No assignments generated')
            self.logger.warning('No assignments generated')
            return

        self.publish_assignments(assignments)
        self.update_robot_locations(assignments)
        
        # Track assignments
        for robot_name, task_detail, msg in assignments:
            self.assignment_history.append({
                'timestamp': time.time(),
                'robot': robot_name,
                'task': task_detail['task_id'],
                'message': msg
            })
        
        # Keep only last 100 assignments
        if len(self.assignment_history) > 100:
            self.assignment_history = self.assignment_history[-100:]
        
        # Log battery status
        self.get_logger().info('Robot battery status:')
        self.logger.info('Robot battery status:')
        for robot_name, robot_info in self.robots.items():
            self.get_logger().info(f'  {robot_name}: {robot_info["battery"]:.1f}% (type={robot_info["type"]})')
            self.logger.info(f'  {robot_name}: {robot_info["battery"]:.1f}% (type={robot_info["type"]})')
        
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
