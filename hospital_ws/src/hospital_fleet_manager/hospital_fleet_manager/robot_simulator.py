import rclpy
from rclpy.node import Node
from rclpy.executors import ExternalShutdownException
from std_msgs.msg import String
from geometry_msgs.msg import Twist
import logging
from logging.handlers import TimedRotatingFileHandler
import time
import threading
import json
import math


class RobotSimulator(Node):
    def __init__(self):
        super().__init__('robot_simulator')
        self.subscription = self.create_subscription(
            String,
            'task_assignments',
            self.task_callback,
            10,
        )
        self.status_publisher = self.create_publisher(String, 'robot_status', 10)
        self.status_timer = self.create_timer(10.0, self.publish_status)

        # Velocity publishers for each robot
        self.vel_publishers = {}
        self.robot_namespaces = [
            'delivery_1', 'delivery_2', 'delivery_3',
            'cleaning_1', 'cleaning_2',
            'patient_mover_1', 'patient_mover_2',
            'heavy_supply_1', 'lab_courier_1',
            'emergency_1', 'general_1', 'general_2'
        ]
        for ns in self.robot_namespaces:
            self.vel_publishers[ns] = self.create_publisher(
                Twist,
                f'/{ns}/cmd_vel',
                10
            )

        # Setup file logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger('robot_simulator')
        handler = TimedRotatingFileHandler('/tmp/robot_simulator.log', when='midnight', interval=1, backupCount=7)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        # Initialize robots with proper data structure including battery
        self.robots = {
            'delivery_1': {'status': 'idle', 'location': 'MainLobby', 'type': 'delivery', 'battery': 100.0, 'current_task': None},
            'delivery_2': {'status': 'idle', 'location': 'Pharmacy', 'type': 'delivery', 'battery': 100.0, 'current_task': None},
            'delivery_3': {'status': 'idle', 'location': 'ER', 'type': 'delivery', 'battery': 100.0, 'current_task': None},
            'cleaning_1': {'status': 'idle', 'location': 'WardA', 'type': 'cleaning', 'battery': 100.0, 'current_task': None},
            'cleaning_2': {'status': 'idle', 'location': 'ICU', 'type': 'cleaning', 'battery': 100.0, 'current_task': None},
            'patient_mover_1': {'status': 'idle', 'location': 'ER', 'type': 'patient_mover', 'battery': 100.0, 'current_task': None},
            'patient_mover_2': {'status': 'idle', 'location': 'Recovery', 'type': 'patient_mover', 'battery': 100.0, 'current_task': None},
            'heavy_supply_1': {'status': 'idle', 'location': 'Supply', 'type': 'heavy_supply', 'battery': 100.0, 'current_task': None},
            'lab_courier_1': {'status': 'idle', 'location': 'Lab', 'type': 'lab_courier', 'battery': 100.0, 'current_task': None},
            'emergency_1': {'status': 'idle', 'location': 'ER', 'type': 'emergency_response', 'battery': 100.0, 'current_task': None},
            'general_1': {'status': 'idle', 'location': 'MainLobby', 'type': 'general', 'battery': 100.0, 'current_task': None},
            'general_2': {'status': 'idle', 'location': 'Cafeteria', 'type': 'general', 'battery': 100.0, 'current_task': None},
        }
        
        # Battery decay timer (every 5 seconds, simulate battery drain)
        self.battery_timer = self.create_timer(5.0, self.update_battery_levels)
        
        self.logger.info('Robot simulator initialized with Gazebo integration')
        self.get_logger().info('Robot simulator initialized with Gazebo integration')

    def task_callback(self, msg):
        assignment = msg.data
        self.get_logger().info(f'Received assignment: {assignment}')
        self.logger.info(f'Received assignment: {assignment}')
        try:
            robot_name, task = assignment.split(':', 1)
            robot_name = robot_name.strip()
            task = task.strip()
        except ValueError:
            error_msg = f'Could not parse assignment: {assignment}'
            self.get_logger().error(error_msg)
            self.logger.error(error_msg)
            return

        # Async execution
        thread = threading.Thread(target=self.simulate_task, args=(robot_name, task))
        thread.daemon = True
        thread.start()

    def simulate_task(self, robot_name, task):
        state = self.robots.get(robot_name, {})
        if state.get('status') == 'busy':
            self.logger.warning(f'{robot_name} already busy')
            return
        
        # Preserve existing data and update status
        state['status'] = 'busy'
        state['current_task'] = task
        self.robots[robot_name] = state

        self.get_logger().info(f'[{robot_name}] starts task: {task}')
        self.logger.info(f'[{robot_name}] starts task: {task}')

        # Extract destination from task (e.g., "deliver_meds_1 (Pharmacy -> WardB)")
        try:
            task_desc = task.split('(')[1].split('->')[1].strip().rstrip(')')
            destination = task_desc
        except:
            destination = 'unknown'

        # Simulate movement to destination
        self.move_robot_to_destination(robot_name, destination)

        # Simulate task execution at destination
        time.sleep(5 + hash(task) % 5)  # 5-10s task execution

        self.get_logger().info(f'[{robot_name}] completed task: {task}')
        self.logger.info(f'[{robot_name}] completed task: {task}')

        state['status'] = 'idle'
        state['location'] = destination
        state['current_task'] = None
        self.robots[robot_name] = state

    def move_robot_to_destination(self, robot_name, destination):
        """Simulate robot movement by publishing velocity commands"""
        if robot_name not in self.vel_publishers:
            self.get_logger().error(f'No velocity publisher for {robot_name}')
            return

        publisher = self.vel_publishers[robot_name]

        # Simple movement simulation: move forward for a few seconds
        twist = Twist()
        twist.linear.x = 0.5  # Forward velocity
        twist.angular.z = 0.0  # No rotation

        # Publish movement command for 3 seconds
        for _ in range(30):  # 30 * 0.1s = 3s
            publisher.publish(twist)
            time.sleep(0.1)

        # Stop
        twist.linear.x = 0.0
        publisher.publish(twist)

        self.get_logger().info(f'[{robot_name}] moved to {destination}')

    def update_battery_levels(self):
        """Simulate battery drain for active robots"""
        for robot_name, state in self.robots.items():
            if state.get('status') == 'busy':
                # Drain battery faster when busy (~5-8% per update cycle)
                drain = 6.0 + (hash(robot_name) % 4)  # 6-10% drain per 5 seconds
            else:
                # Slow drain when idle (~0.5% per update cycle)
                drain = 0.5 + (hash(robot_name) % 2) * 0.25  # 0.5-1% drain per 5 seconds
            
            current_battery = state.get('battery', 100.0)
            new_battery = max(0.0, current_battery - drain)
            
            # Recharge if idle and battery below 30%
            if state.get('status') == 'idle' and new_battery < 30.0:
                new_battery = min(100.0, new_battery + 1.5)  # Slow recharge
            
            state['battery'] = round(new_battery, 1)
            self.robots[robot_name] = state
        
        # Publish updated status
        try:
            self.publish_status()
        except:
            pass  # Ignore publish errors during timer callback

    def publish_status(self):
        status_data = json.dumps(self.robots)
        msg = String()
        msg.data = status_data
        self.status_publisher.publish(msg)
        self.logger.info(f'Published status: {status_data}')


def main(args=None):
    rclpy.init(args=args)
    node = RobotSimulator()
    node.get_logger().info('Robot simulator node started')
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
