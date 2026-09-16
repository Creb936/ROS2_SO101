import os

from launch import LaunchDescription

from launch.actions import (
    IncludeLaunchDescription,
    TimerAction,
    AppendEnvironmentVariable,
)

from launch.launch_description_sources import PythonLaunchDescriptionSource

from launch_ros.actions import Node, SetParameter

from ament_index_python.packages import get_package_share_directory

from launch.substitutions import Command
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():

    pkg_description = get_package_share_directory("so101_description")
    pkg_moveit = get_package_share_directory("so101_moveit_config")

    # ---------------------------------------------------------
    # Global simulation time
    # Applies to MoveIt and RViz nodes launched below
    # ---------------------------------------------------------
    use_sim_time = SetParameter(
        name="use_sim_time",
        value=True,
    )

    # ---------------------------------------------------------
    # Gazebo resource path
    # ---------------------------------------------------------
    workspace_share_dir = os.path.join(pkg_description, "..")

    set_env = AppendEnvironmentVariable(
        "GZ_SIM_RESOURCE_PATH",
        workspace_share_dir,
    )

    # ---------------------------------------------------------
    # Robot description
    # ---------------------------------------------------------
    xacro_file = os.path.join(
        pkg_description,
        "urdf",
        "dual_so101.urdf.xacro",
    )

    robot_description = ParameterValue(
        Command([
            "xacro",
            " ",
            xacro_file,
        ]),
        value_type=str,
    )

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        parameters=[
            {
                "robot_description": robot_description,
                "use_sim_time": True,
            }
        ],
        output="screen",
    )

    # ---------------------------------------------------------
    # Gazebo Harmonic
    # ---------------------------------------------------------
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory("ros_gz_sim"),
                "launch",
                "gz_sim.launch.py",
            )
        ),
        launch_arguments={
            "gz_args": "-r empty.sdf"
        }.items(),
    )

    # ---------------------------------------------------------
    # Spawn robot into Gazebo
    # ---------------------------------------------------------
    spawn_entity = Node(
        package="ros_gz_sim",
        executable="create",
        arguments=[
            "-name",
            "dual_so101",
            "-topic",
            "robot_description",
            "-z",
            "0.01",
        ],
        output="screen",
    )

    # ---------------------------------------------------------
    # Gazebo clock -> ROS clock
    # ---------------------------------------------------------
    clock_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        arguments=[
            "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock"
        ],
        output="screen",
    )

    # ---------------------------------------------------------
    # ros2_control controllers
    # Gazebo's gz_ros2_control creates controller_manager
    # ---------------------------------------------------------
    controller_spawner_common = [
        "--controller-manager",
        "/controller_manager",
    ]

    # 1. Joint State Broadcaster
    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "joint_state_broadcaster",
            *controller_spawner_common,
        ],
        output="screen",
    )

    # 2. Arm 1 controller
    arm1_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "arm1_controller",
            *controller_spawner_common,
        ],
        output="screen",
    )

    # 3. Arm 2 controller
    arm2_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "arm2_controller",
            *controller_spawner_common,
        ],
        output="screen",
    )

    # 4. Arm 1 gripper
    arm1_gripper_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "arm1_gripper_controller",
            *controller_spawner_common,
        ],
        output="screen",
    )

    # 5. Arm 2 gripper
    arm2_gripper_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "arm2_gripper_controller",
            *controller_spawner_common,
        ],
        output="screen",
    )

    # ---------------------------------------------------------
    # Start controllers sequentially with delays
    #
    # t = 5 s  : joint_state_broadcaster
    # t = 7 s  : arm1_controller
    # t = 9 s  : arm2_controller
    # t = 11 s : arm1_gripper_controller
    # t = 13 s : arm2_gripper_controller
    # ---------------------------------------------------------
    delayed_controllers = TimerAction(
        period=5.0,
        actions=[
            joint_state_broadcaster_spawner,

            TimerAction(
                period=2.0,
                actions=[
                    arm1_controller_spawner,
                ],
            ),

            TimerAction(
                period=4.0,
                actions=[
                    arm2_controller_spawner,
                ],
            ),

            TimerAction(
                period=6.0,
                actions=[
                    arm1_gripper_controller_spawner,
                ],
            ),

            TimerAction(
                period=8.0,
                actions=[
                    arm2_gripper_controller_spawner,
                ],
            ),
        ],
    )

    # ---------------------------------------------------------
    # MoveIt move_group
    # ---------------------------------------------------------
    move_group = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                pkg_moveit,
                "launch",
                "move_group.launch.py",
            )
        )
    )

    # ---------------------------------------------------------
    # MoveIt RViz
    # ---------------------------------------------------------
    moveit_rviz = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                pkg_moveit,
                "launch",
                "moveit_rviz.launch.py",
            )
        )
    )

    # ---------------------------------------------------------
    # Launch everything
    # ---------------------------------------------------------
    return LaunchDescription([
        set_env,

        # Make simulation time available to included MoveIt/RViz nodes
        use_sim_time,

        robot_state_publisher,
        gazebo,
        spawn_entity,
        clock_bridge,

        delayed_controllers,

        move_group,
        moveit_rviz,
    ])