from launch import LaunchDescription
import os
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.substitutions import FindPackageShare
from launch.substitutions import PathJoinSubstitution


def generate_launch_description():
    scenario_arg = DeclareLaunchArgument(
        "scenario_file",
        default_value="",
        description="Optional scenario YAML path for scheduler/simulator",
    )
    visual_dashboard_arg = DeclareLaunchArgument(
        "use_visual_dashboard",
        default_value="true",
        description="Start visual dashboard node",
    )
    basic_dashboard_arg = DeclareLaunchArgument(
        "use_basic_dashboard",
        default_value="false",
        description="Start basic dashboard node",
    )
    gazebo_arg = DeclareLaunchArgument(
        "use_gazebo",
        default_value="false",
        description="Launch Gazebo simulation environment",
    )
    nav2_arg = DeclareLaunchArgument(
        "use_nav2",
        default_value="false",
        description="Enable Nav2 stacks inside Gazebo launch",
    )
    state_publishers_arg = DeclareLaunchArgument(
        "use_state_publishers",
        default_value="false",
        description="Enable robot_state_publisher nodes in Gazebo launch",
    )
    gz_gui_arg = DeclareLaunchArgument(
        "use_gz_gui",
        default_value="true",
        description="Enable Gazebo GUI (set false for headless server mode)",
    )

    env = {"HOSPITAL_SCENARIO_FILE": LaunchConfiguration("scenario_file")}

    python_exec = os.environ.get('HOSPITAL_PYTHON', 'python3')

    scheduler = ExecuteProcess(
        cmd=[python_exec, "-m", "hospital_fleet_manager.fleet_scheduler", "--ros-args", "-r", "__node:=fleet_scheduler"],
        name="fleet_scheduler",
        output="screen",
        additional_env=env
    )

    simulator = ExecuteProcess(
        cmd=[python_exec, "-m", "hospital_fleet_manager.robot_simulator", "--ros-args", "-r", "__node:=robot_simulator"],
        name="robot_simulator",
        output="screen",
        additional_env=env
    )

    # If HOSPITAL_USE_GUNICORN is set (default in run script), launch dashboard with gunicorn
    use_gunicorn = os.environ.get('HOSPITAL_USE_GUNICORN', '1')
    dashboard_port = os.environ.get('HOSPITAL_DASHBOARD_PORT', '5000')
    if use_gunicorn and use_gunicorn != '0':
        visual_cmd = [python_exec, '-m', 'gunicorn', f'hospital_fleet_manager.dashboard_visual:app', '--bind', f'0.0.0.0:{dashboard_port}', '--workers', '1', '--threads', '2']
    else:
        visual_cmd = [python_exec, "-m", "hospital_fleet_manager.dashboard_visual", "--ros-args", "-r", "__node:=dashboard_visual"]

    visual_dashboard = ExecuteProcess(
        cmd=visual_cmd,
        name="dashboard_visual",
        output="screen",
        condition=IfCondition(LaunchConfiguration("use_visual_dashboard")),
        additional_env=env
    )

    basic_dashboard = ExecuteProcess(
        cmd=[python_exec, "-m", "hospital_fleet_manager.dashboard", "--ros-args", "-r", "__node:=dashboard"],
        name="dashboard",
        output="screen",
        condition=IfCondition(LaunchConfiguration("use_basic_dashboard")),
        additional_env=env
    )

    gazebo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [
                    FindPackageShare("hospital_fleet_manager"),
                    "launch",
                    "gazebo_hospital.launch.py",
                ]
            )
        ),
        condition=IfCondition(LaunchConfiguration("use_gazebo")),
        launch_arguments={
            "use_nav2": LaunchConfiguration("use_nav2"),
            "use_state_publishers": LaunchConfiguration("use_state_publishers"),
            "use_gz_gui": LaunchConfiguration("use_gz_gui"),
            "use_bridge": "true",
        }.items(),
    )

    return LaunchDescription(
        [
            scenario_arg,
            visual_dashboard_arg,
            basic_dashboard_arg,
            gazebo_arg,
            nav2_arg,
            state_publishers_arg,
            gz_gui_arg,
            gazebo_launch,
            scheduler,
            simulator,
            visual_dashboard,
            basic_dashboard,
        ]
    )
