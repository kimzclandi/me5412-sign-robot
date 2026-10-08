"""Derive a fixed-base MuJoCo model without editing upstream assets."""
from pathlib import Path
import json
import xml.etree.ElementTree as ET
import mujoco

ROOT = Path(__file__).resolve().parents[1]


def main():
    folder = ROOT / "assets/robot"
    vendor = folder / "vendor/g1_29dof_rev_1_0_with_inspire_hand_DFQ.urdf"
    tree = ET.parse(vendor)
    tree.find(".//compiler").set("meshdir", "vendor/meshes")
    for mesh in tree.findall(".//mesh"):
        mesh.set("filename", Path(mesh.get("filename")).name)
    tree.write(folder / "g1_fixed.urdf")
    model = mujoco.MjModel.from_xml_path(str(folder / "g1_fixed.urdf"))
    mujoco.mj_saveLastXML(str(folder / "imported.xml"), model)
    scene = ET.parse(folder / "imported.xml")
    root = scene.getroot()
    ET.SubElement(root, "visual")
    visual = root.find("visual")
    ET.SubElement(visual, "global", offwidth="1280", offheight="960")
    ET.SubElement(visual, "headlight", ambient="0.5 0.5 0.5", diffuse="0.7 0.7 0.7", specular="0.1 0.1 0.1")
    world = root.find("worldbody")
    mount = ET.Element("body", name="fixed_mount", pos="0 0 0.79")
    for item in list(world):
        world.remove(item)
        mount.append(item)
    world.append(mount)
    ET.SubElement(world, "geom", name="floor", type="plane", size="3 3 0.05", rgba="0.13 0.17 0.23 1", contype="0", conaffinity="0")
    ET.SubElement(world, "light", name="key", pos="1 -2 3", dir="-0.3 0.5 -1", diffuse="0.8 0.8 0.8")
    for side in ("left", "right"):
        body = root.find(f".//body[@name='{side}_wrist_yaw_link']")
        ET.SubElement(body, "site", name=f"{side}_palm", pos="0.075 0 0", size="0.003", rgba="0 0 0 0")
    ET.indent(scene)
    scene.write(folder / "scene.xml", encoding="unicode")
    result = mujoco.MjModel.from_xml_path(str(folder / "scene.xml"))
    couplings = []
    for joint in tree.findall("joint"):
        mimic = joint.find("mimic")
        if mimic is not None:
            couplings.append({"child": joint.get("name"), "parent": mimic.get("joint"), "multiplier": float(mimic.get("multiplier", "1")), "offset": float(mimic.get("offset", "0"))})
    info = {"model": "Unitree G1 + Inspire DFQ", "mujoco_version": mujoco.__version__, "nq": result.nq, "nv": result.nv, "nu": result.nu, "equality_constraints": result.neq,
            "couplings": couplings, "fixed_base": True, "execution_mode": "kinematic_qpos_replay", "adaptations": ["Relative mesh path repair", "Fixed mount at z=0.79m", "Lighting, floor, palm reference sites"],
            "limitations": ["No actuator controller; no dynamics or real-robot feasibility claim", "Leg and waist positions held constant in trajectories", "No moving facial expression; head is fixed", "All 12 upstream mimic equalities preserved and replay explicitly obeys their equations"]}
    (folder / "model_info.json").write_text(json.dumps(info, indent=2) + "\n")
    print(json.dumps({k: info[k] for k in ("nq", "nv", "nu", "equality_constraints", "fixed_base")}))


if __name__ == "__main__":
    main()
