import os

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch.substitutions import PathJoinSubstitution


def generate_launch_description():
    pkg_share = FindPackageShare('hospital_fleet_manager').find('hospital_fleet_manager')
    models_path = os.path.join(pkg_share, 'models')
    map_path = os.path.join(pkg_share, 'maps', 'hospital_map.yaml')
    world_path = os.path.join(pkg_share, 'worlds', 'hospital.world')

    env_model_path = SetEnvironmentVariable(
        name='GZ_MODEL_PATH',
        value=models_path
    )

    env_gazebo_model_path = SetEnvironmentVariable(
        name='GAZEBO_MODEL_PATH',
        value=models_path
    )

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('ros_gz_sim'),
                'launch',
                'gz_sim.launch.py'
            ])
        ]),
        launch_arguments={
            'gz_args': world_path,
            'on_exit_shutdown': 'true'
        }.items()
    )

    bridge_args = []
    robot_names = [f'robot_{i}' for i in range(1, 8)]
    for robot_name in robot_names:
        bridge_args.append(f'/{robot_name}/cmd_vel@geometry_msgs/msg/Twist@gz.msgs.Twist')
        bridge_args.append(f'/{robot_name}/odom@nav_msgs/msg/Odometry@gz.msgs.Odometry')

    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=bridge_args,
    )

    state_publishers = []
    for robot_name in robot_names:
        state_publishers.append(
            Node(
                package='robot_state_publisher',
                executable='robot_state_publisher',
                name=f'{robot_name}_state_publisher',
                namespace=robot_name,
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
        env_model_path,
        env_gazebo_model_path,
        gazebo,
        bridge,
        *state_publishers,
        *nav_launches,
    ])
