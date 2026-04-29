# AI-Based Hospital Robot Fleet Simulation

A complete ROS 2 Jazzy simulation for an AI-coordinated hospital robot fleet with Gazebo visual support, autonomous navigation, and a live web dashboard.

---

## 📋 Project Structure

```
hospital_ws/
├── src/
│   └── hospital_fleet_manager/
│       ├── package.xml                    # ROS 2 package metadata
│       ├── setup.py                       # Python package setup
│       ├── setup.cfg                      # Setup configuration
│       ├── hospital_fleet_manager/
│       │   ├── __init__.py                # Package init
│       │   ├── fleet_scheduler.py         # Main scheduler node
│       │   ├── robot_simulator.py         # Simulator node
│       │   ├── dashboard.py               # Web dashboard node
│       │   ├── hospital_map.py            # Graph-based hospital topology
│       │   ├── ai_predictor.py            # ML task predictor
│       │   ├── worlds/                    # Gazebo world files
│       │   │   └── hospital.world         # Hospital environment
│       │   ├── models/                    # Robot model files
│       │   │   ├── hospital_robot.urdf
│       │   │   ├── model.config
│       │   │   └── model.sdf
│       │   ├── config/                    # Navigation config
│       │   │   └── nav2_params.yaml
│       │   ├── maps/                      # Map assets for Nav2
│       │   │   ├── hospital_map.pgm
│       │   │   └── hospital_map.yaml
│       │   └── launch/                    # Launch files
│       │       └── gazebo_hospital.launch.py
│       ├── resource/
├── build/                                 # Build artifacts
├── install/                               # Install artifacts
├── run_scheduler.sh                       # Start scheduler
├── run_simulator.sh                       # Start simulator
├── run_gazebo.sh                          # Launch Gazebo + Nav2
├── run_dashboard.sh                       # Launch Flask dashboard
└── README.md                              # This file
```

---

## ✅ New Features

- **Gazebo Harmonic visual simulation** using `ros_gz_sim` and `ros_gz_bridge`
- **Autonomous navigation stack** with `nav2_bringup` for robot path planning
- **Live Flask dashboard** displaying robot status, assignments, and fleet activity
- **Expanded fleet** from 3 to **7 robots** with more diverse hospital tasks
- **Richer hospital topology** with `WardC`, `Supply`, and `MRI`
- **More complex scenarios** including supply restocking, patient transport, and MRI support

---

## 🛠️ Setup

### Prerequisites

- Ubuntu 24.04 LTS
- ROS 2 Jazzy installed
- Gazebo Harmonic installed
- Python 3.12+ installed

### 1. Virtual environment

```bash
python3 -m venv ~/venv-ai-hospital
source ~/venv-ai-hospital/bin/activate
pip install -U pip
pip install scipy networkx scikit-learn joblib flask
```

### 2. Build the workspace

```bash
source /opt/ros/jazzy/setup.bash
cd ~/Documents/ai-hospital/hospital_ws
colcon build --symlink-install
```

---

## 🚀 Launch the Simulation

### 1. Start Gazebo + Nav2

```bash
cd ~/Documents/ai-hospital/hospital_ws
bash run_gazebo.sh
```

### 2. Start the fleet scheduler

```bash
cd ~/Documents/ai-hospital/hospital_ws
bash run_scheduler.sh
```

### 3. Start the robot simulator

```bash
cd ~/Documents/ai-hospital/hospital_ws
bash run_simulator.sh
```

### 4. Start the dashboard

```bash
cd ~/Documents/ai-hospital/hospital_ws
bash run_dashboard.sh
```

Or start everything together:

```bash
cd ~/Documents/ai-hospital/hospital_ws
bash run_full_stack.sh
```

Then open `http://localhost:5000` in your browser.

---

## 🔍 Notes

- The Gazebo world spawns multiple robots and uses the package's local model path.
- The scheduler now assigns tasks for 7 robots using an AI scheduler with congestion-aware cost prediction.
- The dashboard provides real-time fleet status and a rolling assignment history.

---

## ✅ Verification

- `python3 -m py_compile src/hospital_fleet_manager/hospital_fleet_manager/fleet_scheduler.py`
- `python3 -m py_compile src/hospital_fleet_manager/hospital_fleet_manager/robot_simulator.py`
- `python3 -m py_compile src/hospital_fleet_manager/hospital_fleet_manager/dashboard.py`

---

## 🧩 Recommended Next Step

Open the dashboard at `http://localhost:5000` while the scheduler and simulator are running, then watch the robot fleet assignments in real time.

## Gazebo Setup Note

If you run into Gazebo / gz issues (plugins, GLIBC errors, or missing system plugins), see the project-specific Gazebo notes: [hospital_ws/GZ_SETUP.md](hospital_ws/GZ_SETUP.md#L1).
