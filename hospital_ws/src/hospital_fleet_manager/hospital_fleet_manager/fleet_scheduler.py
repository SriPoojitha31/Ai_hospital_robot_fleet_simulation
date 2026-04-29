import json
import logging
import random
import time
from logging.handlers import TimedRotatingFileHandler

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from scipy.optimize import linear_sum_assignment
from std_msgs.msg import String

from hospital_fleet_manager.ai_predictor import EnhancedAIPredictor
from hospital_fleet_manager.hospital_map import build_hospital_map, shortest_path, shortest_path_length
from hospital_fleet_manager.scenario_loader import load_scenario

try:
    from prometheus_client import Counter, Gauge, start_http_server
except Exception:
    Counter = None
    Gauge = None
    start_http_server = None


class FleetScheduler(Node):
    def __init__(self):
        super().__init__("fleet_scheduler")
        self.publisher = self.create_publisher(String, "task_assignments", 10)

        self.hospital_map = build_hospital_map()
        self.predictor = EnhancedAIPredictor()
        self.scenario = load_scenario()

        self.logger = logging.getLogger("fleet_scheduler")
        self.logger.setLevel(logging.INFO)
        handler = TimedRotatingFileHandler("/tmp/fleet_scheduler.log", when="midnight", interval=1, backupCount=7)
        handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
        if not self.logger.handlers:
            self.logger.addHandler(handler)

        self.robots = self.scenario.get("robots", {})
        self.tasks = list(self.scenario.get("initial_tasks", []))
        self.room_floors = self.scenario.get("room_floors", {})
        self.priority_rank = self.scenario["sla"]["priority_rank"]
        self.deadlines = self.scenario["sla"]["deadline_secs"]

        self.assignment_history = []
        self.active_assignments = {}
        self.edge_load = {}
        self.task_counter = 0

        self._metrics_started = False
        self._metric_cycle = None
        self._metric_reject = None
        self._metric_preempt = None
        self._metric_queue = None
        self._metric_busy = None
        self._init_metrics()

        self.timer = self.create_timer(20.0, self.run_scheduler_cycle)
        self.get_logger().info(f"Scheduler started with scenario: {self.scenario.get('_scenario_path')}")

    def _init_metrics(self):
        if Counter is None or Gauge is None or start_http_server is None:
            return
        try:
            if not self._metrics_started:
                start_http_server(9101)
                self._metrics_started = True
            self._metric_cycle = Counter("fleet_scheduler_cycles_total", "Scheduler cycle count")
            self._metric_reject = Counter("fleet_scheduler_rejections_total", "Task rejections due to policy")
            self._metric_preempt = Counter("fleet_scheduler_preemptions_total", "Task preemptions")
            self._metric_queue = Gauge("fleet_scheduler_queue_size", "Task queue size")
            self._metric_busy = Gauge("fleet_scheduler_busy_robots", "Busy robot count")
        except Exception:
            self._metrics_started = False

    def _emit_structured(self, event, **kwargs):
        record = {"event": event, "ts": round(time.time(), 3)}
        record.update(kwargs)
        self.logger.info(json.dumps(record))

    def _refresh_active_assignments(self):
        now = time.time()
        completed = [r for r, data in self.active_assignments.items() if data.get("finish_time", 0.0) <= now]
        for robot in completed:
            self.active_assignments.pop(robot, None)

    def _nearest_charging_station(self, location):
        stations = self.scenario["charging"]["stations"]
        best = stations[0]
        best_dist = float("inf")
        for station in stations:
            try:
                dist = shortest_path_length(self.hospital_map, location, station)
                if dist < best_dist:
                    best_dist = dist
                    best = station
            except Exception:
                continue
        return best

    def _inject_charge_tasks(self):
        threshold = self.scenario["charging"]["dispatch_threshold"]
        existing = {t.get("task_id", "") for t in self.tasks}
        for robot_name, robot_info in self.robots.items():
            if robot_info.get("battery", 100.0) >= threshold:
                continue
            if robot_name in self.active_assignments:
                continue
            task_id = f"charge_{robot_name}"
            if task_id in existing:
                continue
            station = self._nearest_charging_station(robot_info["location"])
            self.tasks.append(
                {
                    "task_id": task_id,
                    "from": robot_info["location"],
                    "to": station,
                    "priority": "critical",
                    "type": "charge",
                    "duration": 20,
                    "assigned_robot": robot_name,
                    "deadline": int(time.time()) + self.deadlines["critical"],
                }
            )
            existing.add(task_id)

    def generate_dynamic_tasks(self):
        new_tasks = []
        templates = [
            ("delivery", ["Pharmacy", "Supply"], ["WardA", "WardB", "WardC", "ICU"]),
            ("cleaning", ["WardA", "WardB", "WardC", "ER"], ["WardA", "WardB", "WardC", "ER"]),
            ("patient_mover", ["ER", "Trauma"], ["ICU", "PICU", "Recovery"]),
            ("lab_courier", ["Lab"], ["Radiology", "ER", "ICU"]),
            ("heavy_supply", ["Supply", "Sterilization"], ["OperatingRoom1", "OperatingRoom2", "ER"]),
        ]
        priorities = ["critical", "high", "medium", "low"]
        weights = [0.15, 0.3, 0.35, 0.2]

        for _ in range(random.randint(1, 3)):
            if random.random() > 0.6:
                continue
            task_type, src_pool, dst_pool = random.choice(templates)
            self.task_counter += 1
            prio = random.choices(priorities, weights=weights)[0]
            new_tasks.append(
                {
                    "task_id": f"{task_type}_{self.task_counter}",
                    "from": random.choice(src_pool),
                    "to": random.choice(dst_pool),
                    "priority": prio,
                    "type": task_type,
                    "duration": random.randint(5, 20),
                    "generated": True,
                    "deadline": int(time.time()) + self.deadlines.get(prio, 180),
                }
            )
        return new_tasks

    def _priority_value(self, priority):
        return self.priority_rank.get(priority, 1)

    def _route_penalties(self, robot_location, task):
        path_to_pickup = shortest_path(self.hospital_map, robot_location, task["from"])
        path_task = shortest_path(self.hospital_map, task["from"], task["to"])
        full_path = path_to_pickup + path_task[1:]

        nav_cfg = self.scenario["navigation"]
        cap = nav_cfg["corridor_capacity"]
        edge_penalty_weight = nav_cfg["edge_over_capacity_penalty"]

        edge_penalty = 0.0
        for i in range(len(full_path) - 1):
            a, b = full_path[i], full_path[i + 1]
            edge = tuple(sorted((a, b)))
            projected = self.edge_load.get(edge, 0) + 1
            if projected > cap:
                edge_penalty += (projected - cap) * edge_penalty_weight

        floor_transfers = 0
        for i in range(len(full_path) - 1):
            if self.room_floors.get(full_path[i]) != self.room_floors.get(full_path[i + 1]):
                floor_transfers += 1
        floor_penalty = floor_transfers * nav_cfg["floor_transfer_penalty"]

        return edge_penalty + floor_penalty, full_path

    def _battery_reject(self, robot_info, total_distance):
        charging = self.scenario["charging"]
        required = total_distance * charging["energy_per_distance"] + charging["reserve_percent"]
        return robot_info["battery"] < required

    def compute_cost_matrix(self):
        robot_names = list(self.robots.keys())
        tasks = self.tasks
        cost_matrix = []

        specialty_match = {
            "delivery": ["delivery", "general", "lab_courier"],
            "cleaning": ["cleaning", "general"],
            "patient_mover": ["patient_mover", "emergency_response", "general"],
            "lab_courier": ["lab_courier", "delivery", "general"],
            "heavy_supply": ["heavy_supply", "general"],
            "charge": ["delivery", "cleaning", "patient_mover", "lab_courier", "heavy_supply", "emergency_response", "general"],
        }

        for robot_name in robot_names:
            robot = self.robots[robot_name]
            row = []
            for task in tasks:
                if task.get("assigned_robot") and task["assigned_robot"] != robot_name:
                    row.append(1e9)
                    continue

                distance_to_pickup = shortest_path_length(self.hospital_map, robot["location"], task["from"])
                distance_task = shortest_path_length(self.hospital_map, task["from"], task["to"])
                total_distance = distance_to_pickup + distance_task

                if self._battery_reject(robot, total_distance):
                    row.append(1e9)
                    if self._metric_reject:
                        self._metric_reject.inc()
                    continue

                penalty, _ = self._route_penalties(robot["location"], task)
                congestion = self.estimate_congestion(total_distance)
                predicted_time = self.predictor.predict(total_distance, congestion)

                spec_bonus = -2.0 if robot["type"] in specialty_match.get(task["type"], ["general"]) else 0.0
                slack = max(1, task.get("deadline", int(time.time()) + 180) - int(time.time()))
                sla_urgency = 12.0 / slack

                busy_penalty = 0.0
                current = self.active_assignments.get(robot_name)
                if current:
                    incoming_prio = task.get("priority", "medium")
                    if incoming_prio == "critical" and current.get("priority") in self.scenario["sla"]["preemptable_levels"]:
                        busy_penalty = 8.0
                    else:
                        row.append(1e9)
                        continue

                cost = predicted_time + penalty + busy_penalty + sla_urgency + spec_bonus
                row.append(cost)
            cost_matrix.append(row)

        return robot_names, tasks, cost_matrix

    @staticmethod
    def estimate_congestion(distance):
        return max(0.0, distance - 2.0)

    def assign_tasks(self):
        if not self.tasks:
            return []

        robot_names, tasks, cost_matrix = self.compute_cost_matrix()
        if not cost_matrix or not cost_matrix[0]:
            return []

        row_ind, col_ind = linear_sum_assignment(cost_matrix)
        assignments = []
        for r, t in zip(row_ind, col_ind):
            if cost_matrix[r][t] >= 1e8:
                continue
            robot_name = robot_names[r]
            task = tasks[t]

            # Preemption for critical tasks.
            current = self.active_assignments.get(robot_name)
            if current and task.get("priority") == "critical":
                if self._priority_value(current.get("priority", "low")) < self._priority_value("critical"):
                    self._emit_structured("preempt", robot=robot_name, from_task=current.get("task_id"), to_task=task["task_id"])
                    if self._metric_preempt:
                        self._metric_preempt.inc()

            assignment_msg = (
                f"{robot_name}: {task['task_id']} ({task['from']} -> {task['to']}) "
                f"[priority={task.get('priority', 'medium')},type={task.get('type', 'general')}]"
            )
            assignments.append((robot_name, task, assignment_msg))

        return assignments

    def _update_corridor_load(self, robot_name, task):
        path_to_pickup = shortest_path(self.hospital_map, self.robots[robot_name]["location"], task["from"])
        path_task = shortest_path(self.hospital_map, task["from"], task["to"])
        full_path = path_to_pickup + path_task[1:]
        for i in range(len(full_path) - 1):
            edge = tuple(sorted((full_path[i], full_path[i + 1])))
            self.edge_load[edge] = self.edge_load.get(edge, 0) + 1

    def publish_assignments(self, assignments):
        now = time.time()
        for robot_name, task, assignment_msg in assignments:
            msg = String()
            msg.data = assignment_msg
            self.publisher.publish(msg)

            duration = task.get("duration", 10)
            self.active_assignments[robot_name] = {
                "task_id": task["task_id"],
                "priority": task.get("priority", "medium"),
                "finish_time": now + duration,
            }
            self._update_corridor_load(robot_name, task)

            self.get_logger().info(f"Published assignment: {assignment_msg}")
            self._emit_structured("assignment", robot=robot_name, task=task["task_id"], priority=task.get("priority"), task_type=task.get("type"))

    def update_robot_locations(self, assignments):
        for robot_name, task, _ in assignments:
            self.robots[robot_name]["location"] = task["to"]
            if task.get("type") == "charge":
                self.robots[robot_name]["battery"] = self.scenario["charging"]["target_percent"]
            else:
                self.robots[robot_name]["battery"] = max(0.0, self.robots[robot_name]["battery"] - random.uniform(2.0, 3.5))

    def _prune_task_queue(self, assignments):
        assigned_ids = {task["task_id"] for _, task, _ in assignments}
        self.tasks = [t for t in self.tasks if t.get("task_id") not in assigned_ids]
        if len(self.tasks) > 40:
            self.tasks = self.tasks[-40:]

    def run_scheduler_cycle(self):
        self._refresh_active_assignments()
        self._inject_charge_tasks()

        new_tasks = self.generate_dynamic_tasks()
        self.tasks.extend(new_tasks)
        assignments = self.assign_tasks()
        if assignments:
            self.publish_assignments(assignments)
            self.update_robot_locations(assignments)
            self._prune_task_queue(assignments)

            for robot_name, task, msg in assignments:
                self.assignment_history.append(
                    {
                        "timestamp": time.time(),
                        "robot": robot_name,
                        "task": task["task_id"],
                        "message": msg,
                    }
                )
            if len(self.assignment_history) > 150:
                self.assignment_history = self.assignment_history[-150:]

        if self._metric_cycle:
            self._metric_cycle.inc()
        if self._metric_queue:
            self._metric_queue.set(len(self.tasks))
        if self._metric_busy:
            self._metric_busy.set(len(self.active_assignments))

        self.get_logger().info(f"Cycle done: queued_tasks={len(self.tasks)}, busy={len(self.active_assignments)}")


def main(args=None):
    rclpy.init(args=args)
    node = FleetScheduler()
    node.get_logger().info("Fleet scheduler node started")
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
