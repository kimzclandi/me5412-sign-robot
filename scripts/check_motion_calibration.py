"""Check source-informed qualitative requirements against actual robot FK.

These are robot-only measurements. They are NOT measured human-to-robot errors.
"""
from pathlib import Path
import sys
import json
import hashlib
import numpy as np
import mujoco

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from sign_robot.motion import load_model, load_motion, apply_frame


def main():
    model = load_model()
    data = mujoco.MjData(model)
    motion = load_motion("THANK_YOU")
    points, palms, wrists = [], [], []
    keep = (motion['timestamps_s'] >= 3.0) & (motion['timestamps_s'] <= 4.8)
    for q in motion['positions'][keep]:
        apply_frame(model, data, motion['joint_names'], q)
        palm = data.site('right_palm')
        rotation = palm.xmat.reshape(3, 3)
        wrists.append(palm.xpos.copy())
        # A visible/manual proxy, not a ground-truth measured fingertip marker.
        points.append(palm.xpos + 0.17 * rotation[:, 0])
        palms.append(rotation[:, 1].copy())
    points, palms, wrists = map(np.asarray, (points, palms, wrists))
    # Validate the palm convention using the direction of physical finger flexion.
    zero = mujoco.MjData(model)
    mujoco.mj_forward(model, zero)
    origin = zero.body('R_index_intermediate').xpos.copy()
    wrist_rotation = zero.body('right_wrist_yaw_link').xmat.reshape(3, 3).copy()
    for joint in ('R_index_proximal_joint', 'R_index_intermediate_joint'):
        zero.qpos[model.joint(joint).qposadr[0]] = 0.3
    mujoco.mj_forward(model, zero)
    flexion_displacement = wrist_rotation.T @ (zero.body('R_index_intermediate').xpos - origin)
    head_boxes = []
    for geom in range(model.ngeom):
        if int(model.geom_type[geom]) == int(mujoco.mjtGeom.mjGEOM_MESH) and model.mesh(int(model.geom_dataid[geom])).name == 'head_link':
            mesh = int(model.geom_dataid[geom])
            offset, count = int(model.mesh_vertadr[mesh]), int(model.mesh_vertnum[mesh])
            vertices = model.mesh_vert[offset:offset+count] @ data.geom_xmat[geom].reshape(3, 3).T + data.geom_xpos[geom]
            head_boxes.append((vertices.min(axis=0), vertices.max(axis=0)))
    head_min, head_max = head_boxes[0]
    gap_lower_bound = np.linalg.norm(np.maximum(0, np.maximum(head_min-points[0], points[0]-head_max)))
    report = {
        'action_id': 'THANK_YOU',
        'status': 'agent_engineering_calibration_not_human_ASL_review',
        'source_id': 'lifeprint_thank_you',
        'source_url': 'https://www.lifeprint.com/asl101/pages-signs/t/thankyou.htm',
        'demonstration_video_url': 'https://www.youtube.com/watch?v=2W0BDFUjsG0',
        'video_observation_method': 'A1 agent played and paused the official video, checked screenshots and DOM video.currentTime; monocular qualitative observation, no downloaded pose data',
        'source_video_duration_s': 2.341,
        'source_to_robot_phase_alignment': [
            {'source_times_s': [0.383, 0.716], 'observation': 'Preparation: hand rises from rest toward lower face', 'robot_interval_s': [0.0, 2.5]},
            {'source_times_s': [0.916, 1.016], 'observation': 'Fingers near lips; back of hand toward viewer, palm toward signer', 'robot_interval_s': [2.5, 3.0], 'remaining_difference': 'Robot uses a separated lower-face proxy; no lips or contact'},
            {'source_times_s': [1.050, 1.116], 'observation': 'Hand leaves lips, moves forward and down; palm progressively turns upward', 'robot_interval_s': [3.0, 4.8]},
            {'source_times_s': [1.516], 'observation': 'Extended hand, palm up, fingers toward recipient', 'robot_interval_s': [4.8, 5.4]},
            {'source_times_s': [1.983], 'observation': 'Hand has returned down', 'robot_interval_s': [5.4, 8.0]}
        ],
        'timing_note': 'Robot timing is deliberately slower for research visualization; no human speed-matching claim',
        'method': 'Qualitative 2D reference observations -> manual engineering targets -> bounded IK -> robot FK checks',
        'trajectory_sha256': hashlib.sha256((ROOT / 'motions/THANK_YOU.npz').read_bytes()).hexdigest(),
        'robot_coordinate_system': 'metres; +X forward, +Y robot left, +Z upward; pelvis fixed at world z=0.79',
        'reference_requirements': [
            {'requirement': 'Dominant flat hand; fingertips initially near lips/lower face', 'implementation': 'Open right hand; fingertips aimed at a lower-face proxy', 'status': 'approximation', 'remaining_deviation': 'No model lips, no actual lip contact; source fingers together cannot be matched exactly by this fixed-spacing hand'},
            {'requirement': 'Move forward toward recipient and slightly downward', 'implementation': '12 intermediate wrist-pose targets; Slerp rotation and descending fingertip proxy', 'status': 'robot_path_check_passed'},
            {'requirement': 'End with palm up', 'implementation': 'Right-palm normal aligned with world +Z', 'status': 'robot_orientation_check_passed'},
            {'requirement': 'Smile/nonmanual component', 'implementation': None, 'status': 'not_implemented'}
        ],
        'robot_measurements': {
            'execution_interval_s': [3.0, 4.8],
            'fingertip_proxy_definition': 'right_palm site position + 0.17m times local hand longitudinal +X axis',
            'proxy_start_m': points[0].tolist(), 'proxy_end_m': points[-1].tolist(),
            'forward_displacement_m': float(points[-1, 0] - points[0, 0]),
            'vertical_displacement_m': float(points[-1, 2] - points[0, 2]),
            'maximum_upward_detour_above_start_m': float(points[:, 2].max() - points[0, 2]),
            'minimum_forward_step_m': float(np.diff(points[:, 0]).min()),
            'palm_normal_start': palms[0].tolist(), 'palm_normal_end': palms[-1].tolist(),
            'palm_normal_definition': 'Right wrist local +Y: verified by positive finger flexion moving toward +Y; local +X points longitudinally along fingers',
            'finger_flexion_validation_displacement_in_wrist_frame_m': flexion_displacement.tolist(),
            'head_mesh_world_aabb_m': [head_min.tolist(), head_max.tolist()],
            'start_proxy_to_head_aabb_distance_lower_bound_m': float(gap_lower_bound),
            'gap_interpretation': 'A lower bound to the head surface, not a lip measurement; source near-lip contact is not reproduced',
            'max_keyframe_position_error_m': max(x['position_error_m'] for x in motion['metadata']['keyframe_ik']),
            'keyframe_error_compares_to': 'Agent-authored engineering targets only, not tracked human joints'
        },
        'not_measured': ['Human 3D poses or timing', 'Human-to-robot tracking error', 'ASL user comprehensibility', 'Clinical communication safety'],
        'review_images': [f'results/previews/THANK_YOU_{name}.png' for name in ('start', 'middle', 'end')],
        'retained_development_failures': ['motions/development_failures/THANK_YOU_v1', 'motions/development_failures/THANK_YOU_v2', 'motions/development_failures/THANK_YOU_v3', 'motions/development_failures/THANK_YOU_v4', 'motions/development_failures/THANK_YOU_v5']
    }
    assert report['robot_measurements']['minimum_forward_step_m'] > -0.001
    assert report['robot_measurements']['maximum_upward_detour_above_start_m'] < 0.005
    assert palms[-1, 2] > 0.99
    destination = ROOT / 'results/previews/THANK_YOU_calibration.json'
    destination.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report['robot_measurements'], indent=2))


if __name__ == '__main__':
    main()
