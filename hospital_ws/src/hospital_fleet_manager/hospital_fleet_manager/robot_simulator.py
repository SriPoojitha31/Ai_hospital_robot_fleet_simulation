import json
import logging
import threading
import time
from logging.handlers import TimedRotatingFileHandler

import rclpy
from geometry_msgs.msg import Twist
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import String

from hospital_fleet_manager.scenario_loader import load_scenario

try:
    from prometheus_client import Counter, Gauge, start_http_server
except Exception:
    Counter = None
    Gauge = None
    start_http_server = None


class RobotSimulator(Node):
    def __init__(self):
        super().__init__("robot_simulator")
        self.scenario = load_scenario()

        self.subscription = self.create_subscription(String, "task_assignments", self.task_callback, 10)
        self.status_publisher = self.create_publisher(String, "robot_status", 10)
        self.status_timer = self.create_timer(3.0, self.publish_status)

        self.vel_publishers = {}
        self.logger = logging.getLogger("robot_simulator")
        self.logger.setLevel(logging.INFO)
        handler = TimedRotatingFileHandler("/tmp/robot_simulator.log", when="midnight", interval=1, backupCount=7)
        handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
        if not self.logger.handlers:
            self.logger.addHandler(handler)

        self.robots = {}
        for name, info in self.scenario.get("robots", {}).items():
            self.robots[name] = {
                "status": "idle",
                "location": info["location"],
                "type": info["type"],
                "battery": float(info.get("battery", 100.0)),
                "current_task": None,
            }
            self.vel_publishers[name] = self.create_publisher(Twist, f"/{name}/cmd_vel", 10)

        self.room_floors = self.scenario.get("room_floors", {})
        self.corridor_capacity = int(self.scenario["navigation"]["corridor_capacity"])
        self.active_movements = 0
        self.move_lock = threading.Lock()

        self._metrics_started = False
        self._metric_completed = None
        self._metric_recharged = None
        self._metric_busy = None
        self._init_metrics()

        self.battery_timer = self.create_timer(5.0, self.update_battery_levels)
        self.get_logger().info("Robot simulator initialized with scenario-based behavior")

    def _init_metrics(self):
        if Counter is None or Gauge is None or start_http_server is None:
            return
        try:
            if not self._metrics_started:
                start_http_server(9102)
                self._metrics_started = True
            self._metric_completed = Counter("robot_simulator_tasks_completed_total", "Completed tasks")
            self._metric_recharged = Counter("robot_simulator_charge_cycles_total", "Charge cycle completions")
            self._metric_busy = Gauge("robot_simulator_busy_robots", "Busy robots")
        except Exception:
            self._metrics_started = False

    def _emit_structured(self, event, **kwargs):
        payload = {"event": event, "ts": round(time.time(), 3)}
        payload.update(kwargs)
        self.logger.info(json.dumps(payload))

    def _parse_assignment(self, assignment):
        robot_name, task_desc = assignment.split(":", 1)
        robot_name = robot_name.strip()
        task_desc = task_desc.strip()

        task_type = "general"
        if "[" in task_desc and "]" in task_desc:
            meta = task_desc.split("[", 1)[1].split("]", 1)[0]
            for item in meta.split(","):
                k, _, v = item.partition("=")
                if k.strip() == "type":
                    task_type = v.strip()

        destination = "unknown"
        if "(" in task_desc and "->" in task_desc and ")" in task_desc:
            destination = task_desc.split("(", 1)[1].split("->", 1)[1].split(")", 1)[0].strip()

        task_id = task_desc.split(" ", 1)[0].strip()
        return robot_name, task_id, task_desc, destination, task_type

    def task_callback(self, msg):
        assignment = msg.data
        try:
            robot_name, task_id, task_desc, destination, task_type = self._parse_assignment(assignment)
        except Exception:
            self.get_logger().error(f"Could not parse assignment: {assignment}")
            return

        if robot_name not in self.robots:
            self.get_logger().warning(f"Unknown robot in assignment: {robot_name}")
            return

        thread = threading.Thread(
            target=self.simulate_task,
            args=(robot_name, task_id, task_desc, destination, task_type),
            daemon=True,
        )
        thread.start()

    def _floor_transfer_delay(self, start_room, end_room):
        start_floor = self.room_floors.get(start_room)
        end_floor = self.room_floors.get(end_room)
        if start_floor and end_floor and start_floor != end_floor:
            return 3.5
        return 0.0

    def simulate_task(self, robot_name, task_id, task_desc, destination, task_type):
        state = self.robots[robot_name]
        if state.get("status") == "busy":
            self.logger.warning(f"{robot_name} already busy")
            return

        state["status"] = "busy"
        state["current_task"] = task_desc
        self.robots[robot_name] = state

        self._emit_structured("task_start", robot=robot_name, task=task_id, task_type=task_type, destination=destination)

        self.move_robot_to_destination(robot_name, destination)
        exec_time = 4.0 if task_type == "charge" else (6.0 + (hash(task_id) % 5))
        exec_time += self._floor_transfer_delay(state.get("location"), destination)
        time.sleep(exec_time)

        if task_type == "charge":
            state["battery"] = float(self.scenario["charging"]["target_percent"])
            if self._metric_recharged:
                self._metric_recharged.inc()

        state["status"] = "idle"
        state["location"] = destination
        state["current_task"] = None
        self.robots[robot_name] = state

        if self._metric_completed:
            self._metric_completed.inc()
        self._emit_structured("task_complete", robot=robot_name, task=task_id, task_type=task_type, destination=destination)

    def move_robot_to_destination(self, robot_name, destination):
        if robot_name not in self.vel_publishers:
            return

        with self.move_lock:
            self.active_movements += 1
        try:
            while self.active_movements > self.corridor_capacity:
                time.sleep(0.2)

            publisher = self.vel_publishers[robot_name]
            twist = Twist()
            twist.linear.x = 0.45
            for _ in range(24):
                publisher.publish(twist)
                time.sleep(0.1)
            twist.linear.x = 0.0
            publisher.publish(twist)
        finally:
            with self.move_lock:
                self.active_movements = max(0, self.active_movements - 1)

    def update_battery_levels(self):
        for robot_name, state in self.robots.items():
            if state.get("status") == "busy":
                drain = 5.0 + (hash(robot_name) % 3)
            else:
                drain = 0.4 + (hash(robot_name) % 2) * 0.2

            new_level = max(0.0, state.get("battery", 100.0) - drain)
            if state.get("status") == "idle" and state.get("location") in self.scenario["charging"]["stations"] and new_level < self.scenario["charging"]["target_percent"]:
                new_level = min(self.scenario["charging"]["target_percent"], new_level + 2.5)
            state["battery"] = round(new_level, 1)

        if self._metric_busy:
            self._metric_busy.set(sum(1 for s in self.robots.values() if s.get("status") == "busy"))

    def publish_status(self):
        msg = String()
        msg.data = json.dumps(self.robots)
        self.status_publisher.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = RobotSimulator()
    node.get_logger().info("Robot simulator node started")
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
