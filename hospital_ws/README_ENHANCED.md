# 🤖 AI Hospital Robot Fleet Management System

## 🌟 Overview

A comprehensive **ROS 2-based autonomous robot fleet management system** for hospital environments with advanced features including:

✅ **12-Robot Fleet** with specialized types for different hospital tasks
✅ **25+ Hospital Locations** with realistic pathfinding and navigation
✅ **Dynamic Task Generation** creating realistic hospital scenarios
✅ **Robot Specialization** - delivery, cleaning, patient transport, lab couriers, emergency response
✅ **Gazebo Harmonic** - 3D physics-based visual simulation with autonomous navigation
✅ **Navigation2 Stack** - autonomous path planning with costmaps and collision avoidance
✅ **Advanced Dashboard** - real-time fleet monitoring with battery tracking and analytics
✅ **Priority-Based Assignment** - intelligent task scheduling with critical task handling
✅ **Battery Management** - realistic battery drain simulation with power constraints
✅ **Web UI** - modern responsive dashboard with specialization and priority visualization

---

## 📊 System Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Hospital Floor Plan (25+ Rooms)                        │
│  - Emergency (ER, Trauma, ICU, PICU, NICU, CCU)        │
│  - Medical Wards (WardA-E)                              │
│  - Diagnostics (Lab, Radiology, MRI, Ultrasound, CT)   │
│  - Surgery (3 Operating Rooms + Recovery)              │
│  - Support (Pharmacy, Supply, Sterilization, Cafeteria)│
│  - Admin (Administration, Morgue, Physical Therapy)    │
│  - Nursing Stations (North, South, East)               │
└─────────────────────────────────────────────────────────┘
                          ↓
        Fleet Scheduler (Hungarian Algorithm)
                          ↓
            Priority-Aware Task Assignment
                          ↓
    ┌─────────────────────┬──────────────────┐
    ↓                     ↓                  ↓
Delivery    Cleaning    Patient Movers    Lab Couriers
Robots      Robots      + Emergency       + Supply
(3)         (2)         Response (4)      Robots (3)
```

---

## 🚀 Quick Start

### Prerequisites
- ROS 2 Jazzy on Ubuntu 24.04 LTS
- Gazebo Harmonic
- Navigation2 stack
- Python 3.12 with venv

### Installation

```bash
cd ~/Documents/ai-hospital/hospital_ws
source /opt/ros/jazzy/setup.bash

# Install dependencies
rosdep install --from-paths src --ignore-src -r -y
sudo apt install -y ros-jazzy-ros-gz* ros-jazzy-nav2-* python3-flask

# Build package
colcon build

# Setup virtual environment
python3 -m venv ~/venv-ai-hospital
source ~/venv-ai-hospital/bin/activate
pip install scipy networkx scikit-learn joblib pyyaml flask
```

### Launch Full System

```bash
# Option 1: Run everything at once
cd ~/Documents/ai-hospital/hospital_ws
bash run_full_stack.sh

# Option 2: Launch components separately
# Terminal 1: Gazebo simulation
bash run_gazebo.sh

# Terminal 2: Fleet scheduler (in new terminal)
source ~/venv-ai-hospital/bin/activate
source install/setup.bash
ros2 run hospital_fleet_manager fleet_scheduler

# Terminal 3: Robot simulator
ros2 run hospital_fleet_manager robot_simulator

# Terminal 4: Dashboard
bash run_dashboard.sh
```

### Access Dashboard

Open your browser and navigate to: **http://localhost:5000**

---

## 🤖 Robot Fleet Specifications

### 12-Robot Fleet with Specialization

#### Delivery Robots (3)
- **Purpose:** General medication and light item transport
- **Specialization:** delivery
- **Starting Locations:** MainLobby, Pharmacy, ER
- **Capabilities:** Fast routing for standard deliveries

#### Cleaning Robots (2)
- **Purpose:** Room sanitation and environmental cleaning
- **Specialization:** cleaning
- **Starting Locations:** WardA, ICU
- **Special Behavior:** Extended task duration for thorough cleaning

#### Patient Mover Robots (2)
- **Purpose:** Safe patient transport between departments
- **Specialization:** patient_mover
- **Starting Locations:** ER, Recovery
- **Critical Priority:** Highest scheduler priority for patient-related tasks

#### Heavy Supply Robots (1)
- **Purpose:** Transport large equipment and bulk supplies
- **Specialization:** heavy_supply
- **Starting Locations:** Supply
- **Capability:** Handle equipment that other robots cannot

#### Lab Courier Robots (1)
- **Purpose:** Sample and result transport between lab and departments
- **Specialization:** lab_courier
- **Starting Locations:** Lab
- **Efficiency:** Optimized for frequent small-distance deliveries

#### Emergency Response Robot (1)
- **Purpose:** Priority emergency task handling
- **Specialization:** emergency_response
- **Starting Locations:** ER
- **Override Ability:** Can interrupt other robots for urgent situations

#### General Purpose Robots (2)
- **Purpose:** Flexible backup and overflow handling
- **Specialization:** general
- **Starting Locations:** MainLobby, Cafeteria
- **Capability:** Can handle any task type in the system

---

## 🏥 Hospital Topology

### 25+ Unique Locations

**Main Access:**
- MainLobby, NorthEntrance, SouthEntrance, EmergencyEntry

**Emergency & Critical Care:**
- ER, Trauma, ICU, PICU, NICU, CCU

**Medical Wards:**
- WardA, WardB, WardC, WardD, WardE

**Diagnostics:**
- Lab, Radiology, MRI, Ultrasound, CT

**Surgery Suite:**
- OperatingRoom1, OperatingRoom2, OperatingRoom3, Recovery

**Support Services:**
- Pharmacy, Cafeteria, Supply, Sterilization

**Administration:**
- Administration, Morgue, Physical Therapy

**Nursing Stations:**
- NursingStationN, NursingStationS, NursingStationE

---

## 📋 Task System

### Dynamic Task Generation

Tasks are **automatically generated** based on realistic hospital patterns:

```python
# Example: Medication delivery with critical priority
{
    "task_id": "delivery_task_42",
    "from": "Pharmacy",
    "to": "ICU",
    "priority": "critical",
    "type": "delivery",
    "duration": 8,
    "generated": True  # Procedurally created
}
```

### Task Priorities

| Priority | Weight | Use Cases |
|----------|--------|-----------|
| **CRITICAL** | 0.5x | Emergency deliveries, urgent patient moves |
| **HIGH** | 0.7x | ER support, operating room supplies |
| **MEDIUM** | 0.9x | Standard ward deliveries, routine cleaning |
| **LOW** | 1.0x | Administrative tasks, non-urgent food delivery |

### Task Types

1. **delivery** - Medication and supply transport
2. **cleaning** - Room sanitation (longer duration)
3. **patient_mover** - Patient transport (critical priority)
4. **lab_courier** - Sample and result routes
5. **heavy_supply** - Equipment and bulk item transport
6. **emergency_response** - Override urgent tasks

---

## 🎯 Intelligent Task Assignment

### Algorithm: Priority-Aware Hungarian Algorithm

```
Cost Calculation:
cost = (predicted_time × priority_weight) + specialization_bonus + battery_penalty

Specialization Bonus:
- Robot type matches task type: -2.0 cost reduction
- General robot handling specialized task: no penalty

Battery Penalty:
- Critical task + robot battery < 30%: +50.0 penalty
- High priority task + robot battery < 50%: +15.0 penalty
```

### Assignment Logic

1. **Specialization Matching** - Prioritize robots with matching specialization
2. **Distance Optimization** - Minimize travel distance using hospital graph
3. **Priority Weighting** - Critical/high tasks get lower costs
4. **Battery Awareness** - Low-battery robots avoid critical tasks
5. **Congestion Estimation** - Account for hospital traffic patterns

---

## 🔋 Battery Management System

### Realistic Battery Simulation

- **Initial Charge:** 100% for all robots
- **Drain Rate:** 2-3% per task completed
- **Low Battery Warning:** < 50% battery
- **Critical Low:** < 25% battery (robots avoid critical tasks)

### Battery Status Display

```
┌─────────────────────┐
│ Avg Battery: 73.4%  │
├─────────────────────┤
│ High (75-100%): 7   │
│ Medium (50-74%): 3  │
│ Low (25-49%): 2     │
│ Critical (<25%): 0  │
└─────────────────────┘
```

---

## 📊 Web Dashboard Features

### Real-Time Monitoring

#### Statistics Cards
- Total Robots (12)
- Robots Busy (live count)
- Robots Idle (live count)
- Average Battery %
- Total Tasks Assigned
- Pending Tasks

#### Robot Status Table
| Column | Information |
|--------|-------------|
| **Robot ID** | Unique robot identifier |
| **Type** | Specialization badge (color-coded) |
| **Status** | busy (red) or idle (green) |
| **Battery** | Visual bar + percentage |
| **Current Task** | Priority tag + task ID |
| **Location** | Current room/location |

#### Fleet Analytics Charts

**1. Robot Status Distribution**
- Doughnut chart: Busy vs Idle robots
- Real-time update every 2 seconds

**2. Fleet Specialization**
- Horizontal bar chart: Robot count by type
- Visual breakdown of specializations

**3. Battery Health**
- Stacked bar chart: High/Medium/Low/Critical ranges
- Color-coded battery status

**4. Task Priority Distribution**
- Pie chart: Critical/High/Medium/Low task breakdown
- Visual task complexity assessment

#### Recent Task Assignments
- Scrollable list (last 30 tasks)
- Color-coded by priority
- Dynamic generation indicator
- Timestamp and robot assignment info

---

## 🛠️ Technical Stack

### Core Middleware
- **ROS 2 Jazzy** - Robot Operating System
- **Gazebo Harmonic** - Physics simulation engine
- **Navigation2** - Autonomous navigation stack

### Task Assignment
- **SciPy** - Hungarian algorithm (linear_sum_assignment)
- **NetworkX** - Graph-based pathfinding
- **scikit-learn** - ML-based task duration prediction

### Web Interface
- **Flask** - Python web framework
- **Chart.js** - Real-time data visualization
- **HTML5/CSS3** - Modern responsive UI

### Development
- **Python 3.12** - Application code
- **pytest** - Unit testing framework
- **ROS 2 launch** - Application orchestration

---

## 📈 Performance Metrics

### System Capacity
- **Fleet Size:** 12 specialized robots
- **Hospital Size:** 25+ departments
- **Task Capacity:** ~100+ tasks tracked history
- **Scheduling Cycle:** 30 seconds
- **Dashboard Update Rate:** 2000 ms (0.5 Hz)

### Gazebo Simulation
- **Physics Engine:** ODE solver
- **Update Rate:** 1000 Hz
- **Realtime Factor:** 1.0x

### Navigation
- **Costmap Update:** 5 Hz (local), 1 Hz (global)
- **Path Planning:** DWB local planner + NavFn global planner
- **Collision Avoidance:** Voxel layer costmap

---

## 🚀 Advanced Features

### Robot Specialization System
```python
specialty_match_bonus = {
    'delivery': ['delivery', 'general'],           # Can do deliveries
    'patient_mover': ['patient_mover', 'emergency_response', 'general'],
    'cleaning': ['cleaning', 'general'],
    'lab_courier': ['lab_courier', 'delivery', 'general'],
    'heavy_supply': ['heavy_supply', 'general'],
    'emergency_response': ['emergency_response', 'patient_mover', 'general'],
}
```

### Dynamic Task Generation
Tasks are **procedurally generated** based on:
- Hospital patterns and probabilities
- Random location pairs from realistic pools
- Priority distribution (60% medium/low for variety)
- Task type specialization matching

### Autonomous Navigation
Each robot runs its own **Navigation2 instance**:
- **Cost Maps:** Laser scan + inflation layer
- **Global Planner:** NavFn (distance field)
- **Local Planner:** DWB (Dynamic Window Approach)
- **Collision Avoidance:** Vector field + velocity space

---

## 📁 Project Structure

```
hospital_ws/
├── src/hospital_fleet_manager/
│   ├── hospital_fleet_manager/
│   │   ├── fleet_scheduler.py        # Main task scheduler (12 robots, dynamic tasks)
│   │   ├── robot_simulator.py        # Robot task execution & movement
│   │   ├── hospital_map.py           # 25+ location graph topology
│   │   ├── ai_predictor.py           # ML-based time prediction
│   │   ├── dashboard_enhanced.py     # Flask web dashboard (NEW)
│   │   ├── models/
│   │   │   ├── model.sdf             # Gazebo robot model
│   │   │   ├── model.config          # Model metadata
│   │   │   └── hospital_robot.urdf   # Robot description
│   │   ├── launch/
│   │   │   └── gazebo_hospital.launch.py  # Complete system launcher
│   │   ├── worlds/
│   │   │   └── hospital.world        # Gazebo world with 12 robots
│   │   ├── config/
│   │   │   ├── nav2_params.yaml      # Nav2 configuration
│   │   │   ├── tasks.yaml            # Task definitions
│   │   │   ├── robots.yaml           # Robot configurations
│   │   │   └── ai.yaml               # AI predictor settings
│   │   └── maps/
│   │       ├── hospital_map.yaml     # Map manifest
│   │       └── hospital_map.pgm      # Occupancy grid
│   └── package.xml
├── run_gazebo.sh                     # Gazebo launcher
├── run_dashboard.sh                  # Dashboard launcher (NEW)
├── run_full_stack.sh                 # All-in-one launcher
└── README.md (this file)
```

---

## 🧪 Validation & Testing

### Python Syntax Validation
```bash
python3 -m py_compile src/hospital_fleet_manager/hospital_fleet_manager/*.py
```

### ROS Package Verification
```bash
ros2 pkg list | grep hospital_fleet_manager
```

### Launch File Testing
```bash
ros2 launch hospital_fleet_manager gazebo_hospital.launch.py
```

---

## 🔧 Configuration Files

### Tasks Configuration (`config/tasks.yaml`)
Define task pools with specialization requirements and priorities

### Robots Configuration (`config/robots.yaml`)
Robot types, starting locations, and capability definitions

### AI Predictor (`config/ai.yaml`)
Machine learning parameters for task duration prediction:
- Base time estimate
- Distance coefficient
- Congestion coefficient

### Navigation (`config/nav2_params.yaml`)
Navigation2 stack tuning:
- Costmap resolution and size
- Planner parameters
- Controller gains

---

## 📚 Key Algorithms

### Hungarian Algorithm (Task Assignment)
Solves minimum cost bipartite matching:
- robots ↔ tasks
- Cost matrix includes distance, priority, battery, specialization
- O(n³) but optimal assignment

### Dijkstra Pathfinding
Hospital graph pathfinding:
- 25+ nodes (rooms/departments)
- 16+ edges (corridors)
- Distance-weighted path planning

### Dynamic Task Generation
Procedural hospital scenario creation:
- Realistic task distribution
- Specialty-constrained pools
- Priority weighting

---

## 🎓 Learning Resources

### ROS 2 Concepts
- Subscribers/Publishers for task flow
- Node architecture with timers
- Launch file composition

### Gazebo Training
- Physics-based simulation
- Model placement and spawning
- Plugin integration (lidar, differential drive)

### Navigation Stack
- Costmap layers and inflation
- Local vs global planning
- Velocity space trajectory evaluation

---

## ⚠️ Known Limitations

1. **Simulation Only:** Current system is ROS 2 simulation, not hardware deployment
2. **Single Floor:** Hospital topology is 2D; no multi-floor support yet
3. **No Charging:** Battery drains but robots don't recharge (future feature)
4. **No Emergencies:** Emergency priority exists but not dynamically triggered
5. **Linear Time Prediction:** AI predictor uses linear regression; neural networks possible

---

## 🚀 Future Enhancements

- [ ] Multi-floor support with elevators
- [ ] Battery charging stations and dock management
- [ ] Emergency situation dynamic task generation
- [ ] Robot failure/unavailability simulation
- [ ] Advanced dashboard with burndown charts
- [ ] Integration with real hospital scheduling systems
- [ ] GPU-accelerated Gazebo rendering
- [ ] ROS 2 Security (DDS encryption)
- [ ] Performance profiling and optimization
- [ ] Hardware deployment pipeline (TurtleBot 4, etc.)

---

## 📖 Documentation

- **Launch Files:** `src/hospital_fleet_manager/launch/README.md`
- **Configuration:** `src/hospital_fleet_manager/config/README.md`
- **API:** Inline docstrings in each Python module

---

## 🤝 Contributing

To extend the system:

1. Add new robot types to `fleet_scheduler.py`
2. Define new tasks in `config/tasks.yaml`
3. Update hospital map in `hospital_map.py`
4. Add new metrics to dashboard in `dashboard_enhanced.py`
5. Test with `pytest` before submitting

---

## 📝 License

This project is for educational and research purposes.

---

## ✨ Summary

This AI Hospital Robot Fleet Management System demonstrates a **complete autonomous fleet solution** with:

✅ 12 specialized robots
✅ Intelligent priority-aware scheduling
✅ Real-time web monitoring
✅ Gazebo Harmonic visualization
✅ Navigation2 autonomous navigation
✅ Dynamic task generation
✅ Battery management simulation

**Perfect for:**
- Autonomous systems research
- Healthcare robotics education
- Fleet management algorithm testing
- ROS 2 + Gazebo learning
- Task scheduling research

---

**Last Updated:** December 2024
**Version:** 2.0 (Enhanced with Specialization, Battery Management, & Dynamic Tasks)
**Maintenance Status:** Active Development
