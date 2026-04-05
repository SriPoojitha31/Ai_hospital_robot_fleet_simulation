import rclpy
from rclpy.node import Node
from rclpy.executors import ExternalShutdownException
from std_msgs.msg import String
import logging
from logging.handlers import TimedRotatingFileHandler
import time
import threading
import json


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

        # Setup file logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger('robot_simulator')
        handler = TimedRotatingFileHandler('/tmp/robot_simulator.log', when='midnight', interval=1, backupCount=7)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        self.robots = {}
        self.logger.info('Robot simulator initialized with async execution and status pub')
        self.get_logger().info('Robot simulator initialized with async execution and status pub')

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
        state = self.robots.setdefault(robot_name, {'status': 'idle', 'location': 'unknown', 'current_task': None})
        if state['status'] == 'busy':
            self.logger.warning(f'{robot_name} already busy')
            return
        state['status'] = 'busy'
        state['current_task'] = task
        self.robots[robot_name] = state

        self.get_logger().info(f'[{robot_name}] starts task: {task}')
        self.logger.info(f'[{robot_name}] starts task: {task}')

        # Simulate real execution time
        time.sleep(10 + hash(task) % 10)  # 10-20s random

        self.get_logger().info(f'[{robot_name}] completed task: {task}')
        self.logger.info(f'[{robot_name}] completed task: {task}')

        state['status'] = 'idle'
        state['current_task'] = None
        self.robots[robot_name] = state

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
