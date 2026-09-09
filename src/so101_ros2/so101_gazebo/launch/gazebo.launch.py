import os

from launch import LaunchDescription
from launch.actions import TimerAction, IncludeLaunchDescription, AppendEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_share_directory
from moveit_configs_utils import MoveItConfigsBuilder

def generate_launch_description():
    pkg_description = get_package_share_directory('so101_description')
    pkg_moveit_config = get_package_share_directory('so101_moveit_config')

    workspace_share_dir = os.path.join(pkg_description, '..')

    # Gazebo resource path
    set_env = AppendEnvironmentVariable(
        'GZ_SIM_RESOURCE_PATH', workspace_share_dir
    )
    os.environ['GZ_SIM_RESOURCE_PATH'] = workspace_share_dir

    # ================================================================
    # 1. MOVEIT CONFIG 
    # ================================================================
    real_urdf_path = os.path.join(pkg_description, 'urdf', 'dual_so101.urdf.xacro')

    moveit_config = (
        MoveItConfigsBuilder(
            'dual_so101_assembly',
            package_name='so101_moveit_config'
        )
        .robot_description(file_path=real_urdf_path)
        .robot_description_semantic(file_path='config/dual_so101_assembly.srdf')
        .trajectory_execution(file_path='config/moveit_controllers.yaml')
        .to_moveit_configs()
    )

    # ================================================================
    # 2. ROBOT STATE PUBLISHER
    # ================================================================
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='both',
        parameters=[
            moveit_config.robot_description,
            {'use_sim_time': True}
        ]
    )

    # ================================================================
    # 3. GAZEBO
    # ================================================================
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                FindPackageShare('ros_gz_sim').find('ros_gz_sim'),
                'launch',
                'gz_sim.launch.py'
            )
        ),
        launch_arguments={'gz_args': '-r empty.sdf'}.items()
    )

    spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-name', 'dual_so101',
            '-topic', 'robot_description',
            '-z', '0.01'
        ],
        output='screen'
    )

    clock_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=['/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'],
        output='screen'
    )

    # ================================================================
    # 4. ROS 2 CONTROL SPAWNERS (ĐÃ TÁCH THỜI GIAN CHỐNG XUNG ĐỘT)
    # ================================================================
    delayed_joint_state_broadcaster = TimerAction(
        period=5.0,
        actions=[
            Node(
                package='controller_manager',
                executable='spawner',
                arguments=['joint_state_broadcaster', '--controller-manager', '/controller_manager'],
                output='screen'
            )
        ]
    )

    # Tay 1 nạp sau 7 giây
    delayed_arm1_controller = TimerAction(
        period=7.0,
        actions=[
            Node(
                package='controller_manager',
                executable='spawner',
                arguments=['arm1_controller', '-c', '/controller_manager'],
                output='screen'
            )
        ]
    )

    # Tay 2 nạp sau 9 giây
    delayed_arm2_controller = TimerAction(
        period=9.0,
        actions=[
            Node(
                package='controller_manager',
                executable='spawner',
                arguments=['arm2_controller', '-c', '/controller_manager'],
                output='screen'
            )
        ]
    )

    # ================================================================
    # 5. MOVE GROUP (BƠM TRỰC TIẾP CARTESIAN LIMITS CHỐNG SẬP)
    # ================================================================
    move_group_node = Node(
        package='moveit_ros_move_group',
        executable='move_group',
        output='screen',
        parameters=[
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.robot_description_kinematics,
            moveit_config.planning_pipelines,
            moveit_config.joint_limits,
            moveit_config.trajectory_execution,
            {'use_sim_time': True},
            # Bơm thông số giới hạn tịnh tiến trực tiếp vào bộ não
            {
                'robot_description_planning.cartesian_limits.max_trans_vel': 1.0,
                'robot_description_planning.cartesian_limits.max_trans_acc': 2.25,
                'robot_description_planning.cartesian_limits.max_trans_dec': -5.0,
                'robot_description_planning.cartesian_limits.max_rot_vel': 1.57
            }
        ]
    )

    # ================================================================
    # 6. RVIZ
    # ================================================================
    delayed_rviz = TimerAction(
        period=5.0,
        actions=[
            Node(
                package='rviz2',
                executable='rviz2',
                name='rviz2',
                output='screen',
                arguments=[
                    '-d',
                    os.path.join(pkg_moveit_config, 'config', 'moveit.rviz')
                ],
                parameters=[
                    moveit_config.robot_description,
                    moveit_config.robot_description_semantic,
                    moveit_config.robot_description_kinematics,
                    moveit_config.planning_pipelines,
                    moveit_config.joint_limits,
                    {'use_sim_time': True}
                ]
            )
        ]
    )

    return LaunchDescription([
        set_env,
        robot_state_publisher,
        gazebo,
        spawn_entity,
        clock_bridge,
        move_group_node,
        delayed_joint_state_broadcaster,
        delayed_arm1_controller,
        delayed_arm2_controller,
        delayed_rviz
    ])