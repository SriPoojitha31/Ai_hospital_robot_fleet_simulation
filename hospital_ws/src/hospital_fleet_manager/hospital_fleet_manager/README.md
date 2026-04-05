# AI-Based Hospital Robot Fleet Simulation

This package includes two ROS 2 nodes:
- `fleet_scheduler`: assigns tasks to robots using the Hungarian algorithm and AI estimated completion times.
- `robot_simulator`: receives assignments, simulates task execution, and logs progress.

Dependencies: `rclpy`, `std_msgs`, `scipy`, `networkx`
