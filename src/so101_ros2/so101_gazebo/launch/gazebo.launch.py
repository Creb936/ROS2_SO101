import os
from launch import LaunchDescription
from launch.actions import TimerAction
from launch.actions import IncludeLaunchDescription, AppendEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch.substitutions import Command
from launch_ros.parameter_descriptions import ParameterValue 
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    pkg_gazebo = FindPackageShare('so101_gazebo').find('so101_gazebo')
    pkg_description = get_package_share_directory('so101_description')
    workspace_share_dir = os.path.join(pkg_description, '..')
    
    set_env = AppendEnvironmentVariable('GZ_SIM_RESOURCE_PATH', workspace_share_dir)
    xacro_file = os.path.join(pkg_description, 'urdf', 'dual_so101.urdf.xacro')
    
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{
            'robot_description': ParameterValue(Command(['xacro ', xacro_file]), value_type=str),
            'use_sim_time': True  # Bật đồng bộ thời gian
        }]
    )

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(FindPackageShare('ros_gz_sim').find('ros_gz_sim'), 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={'gz_args': '-r empty.sdf'}.items()
    )

    spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=['-name', 'dual_so101', '-topic', 'robot_description', '-z', '0.01'],
        output='screen'
    )

    # --- ĐOẠN CODE MỚI THÊM VÀO ---
    
    # 1. Mở RViz2
    rviz2 = Node(
        package='rviz2',
        executable='rviz2',
        # Trỏ tới file config của thư mục description (nếu sếp có)
        arguments=['-d', os.path.join(pkg_description, 'rviz', 'urdf.rviz')],
        parameters=[{'use_sim_time': True}]
    )

    # Cho spawner chờ 5 giây để Gazebo và plugin ros2_control khởi động xong xuôi
    delayed_joint_state_broadcaster = TimerAction(
        period=5.0,
        actions=[
            Node(
                package="controller_manager",
                executable="spawner",
                arguments=["joint_state_broadcaster"],
            )
        ]
    )

    clock_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=['/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'],
        output='screen'
    )

    return LaunchDescription([
        set_env,
        robot_state_publisher,
        gazebo,
        spawn_entity,
        rviz2,
        clock_bridge,
        delayed_joint_state_broadcaster
    ])