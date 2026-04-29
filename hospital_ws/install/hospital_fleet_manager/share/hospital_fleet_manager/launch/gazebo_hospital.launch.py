import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetEnvironmentVariable
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch.substitutions import PathJoinSubstitution


def generate_launch_description():
    pkg_share = FindPackageShare('hospital_fleet_manager').find('hospital_fleet_manager')
    models_path = os.path.join(pkg_share, 'models')
    map_path = os.path.join(pkg_share, 'maps', 'hospital_map.yaml')
    world_path = os.path.join(pkg_share, 'worlds', 'hospital.world')
    gz_resource_path = os.pathsep.join([models_path, pkg_share])

    env_model_path = SetEnvironmentVariable(
        name='GZ_MODEL_PATH',
        value=models_path
    )

    env_gazebo_model_path = SetEnvironmentVariable(
        name='GAZEBO_MODEL_PATH',
        value=models_path
    )

    env_gz_resource_path = SetEnvironmentVariable(
        name='GZ_SIM_RESOURCE_PATH',
        value=gz_resource_path
    )

    env_ign_resource_path = SetEnvironmentVariable(
        name='IGN_GAZEBO_RESOURCE_PATH',
        value=gz_resource_path
    )

    gazebo_gui = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('ros_gz_sim'),
                'launch',
                'gz_sim.launch.py'
            ])
        ]),
        launch_arguments={
            'gz_args': f'-r {world_path}',
            'on_exit_shutdown': 'true'
        }.items(),
        condition=IfCondition(LaunchConfiguration('use_gz_gui')),
    )

    gazebo_headless = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('ros_gz_sim'),
                'launch',
                'gz_sim.launch.py'
            ])
        ]),
        launch_arguments={
            'gz_args': f'-s -r {world_path}',
            'on_exit_shutdown': 'true'
        }.items(),
        condition=UnlessCondition(LaunchConfiguration('use_gz_gui')),
    )

    bridge_args = []
    robot_names = [
        # Delivery robots
        'delivery_1', 'delivery_2', 'delivery_3',
        # Cleaning robots
        'cleaning_1', 'cleaning_2',
        # Patient mover robots
        'patient_mover_1', 'patient_mover_2',
        # Supply and lab robots
        'heavy_supply_1', 'lab_courier_1',
        # Emergency and general robots
        'emergency_1', 'general_1', 'general_2'
    ]
    for robot_name in robot_names:
        bridge_args.append(f'/{robot_name}/cmd_vel@geometry_msgs/msg/Twist@gz.msgs.Twist')
        bridge_args.append(f'/{robot_name}/odom@nav_msgs/msg/Odometry@gz.msgs.Odometry')

    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=bridge_args,
        condition=IfCondition(LaunchConfiguration('use_bridge')),
    )

    state_publishers = []
    for robot_name in robot_names:
        state_publishers.append(
            Node(
                package='robot_state_publisher',
                executable='robot_state_publisher',
                name=f'{robot_name}_state_publisher',
                namespace=robot_name,
                condition=IfCondition(LaunchConfiguration('use_state_publishers')),
                parameters=[{
                    'robot_description': open(os.path.join(pkg_share, 'models', 'hospital_robot.urdf')).read(),
                    'frame_prefix': f'{robot_name}/'
                }],
                remappings=[
                    ('robot_description', f'{robot_name}/robot_description')
                ]
            )
        )

    nav_launches = []
    for robot_name in robot_names:
        nav_launches.append(
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource([
                    PathJoinSubstitution([
                        FindPackageShare('nav2_bringup'),
                        'launch',
                        'bringup_launch.py'
                    ])
                ]),
                condition=IfCondition(LaunchConfiguration('use_nav2')),
                launch_arguments={
                    'namespace': robot_name,
                    'use_namespace': 'True',
                    'map': map_path,
                    'params_file': os.path.join(pkg_share, 'config', 'nav2_params.yaml'),
                    'use_sim_time': 'True',
                    'autostart': 'True'
                }.items()
            )
        )

    return LaunchDescription([
        DeclareLaunchArgument('use_bridge', default_value='true'),
        DeclareLaunchArgument('use_state_publishers', default_value='false'),
        DeclareLaunchArgument('use_nav2', default_value='false'),
        DeclareLaunchArgument('use_gz_gui', default_value='true'),
        env_model_path,
        env_gazebo_model_path,
        env_gz_resource_path,
        env_ign_resource_path,
        gazebo_gui,
        gazebo_headless,
        bridge,
        *state_publishers,
        *nav_launches,
    ])
