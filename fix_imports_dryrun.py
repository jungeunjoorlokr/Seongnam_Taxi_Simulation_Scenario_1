import os
import re

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

REPLACEMENTS = {
    r"\bmodules\.core\.simulator\b": "modules.engine.simulator",
    r"\bmodules\.core\.simulator_object_update\b": "modules.engine.simulator_object_update",
    r"\bmodules\.core\.simulator_helper\b": "modules.engine.simulator_helper",

    r"\bmodules\.services\.default\.extract_data\b": "modules.preprocess.extract_data",
    r"\bmodules\.services\.default\.dispatch_flow\b": "modules.dispatch.dispatch_flow",

    r"\bmodules\.dispatch\.dispatch\b": "modules.dispatch.dispatch",
    r"\bmodules\.dispatch\.dispatch_cost\b": "modules.dispatch.dispatch_cost",
    r"\bmodules\.dispatch\.dispatch_flow\b": "modules.dispatch.dispatch_flow",

    r"\bmodules\.analysis\.dashboard\b": "modules.analytics.dashboard",
    r"\bmodules\.analysis\.figures\.level_of_service\b": "modules.analytics.level_of_service",
    r"\bmodules\.analysis\.figures\.vehicle_operation_status\b": "modules.analytics.vehicle_operation_status",
    r"\bmodules\.analysis\.figures\.spatial_distribution\b": "modules.analytics.spatial_distribution",

    r"\bmodules\.routing\.osrm_routing\b": "modules.routing.osrm_routing",

    r"\bmodules\.point_generator\b": "modules.preprocess.point_generator",

    r"\bmodules\.utils\.utils\b": "modules.utils.utils",
}

def fix_imports_in_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    new_content = content
    for old, new in REPLACEMENTS.items():
        new_content = re.sub(old, new, new_content)

    if new_content != content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"✅ Fixed imports in {file_path}")

def walk_and_fix(root_dir):
    for subdir, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".py"):
                fix_imports_in_file(os.path.join(subdir, file))

if __name__ == "__main__":
    walk_and_fix(PROJECT_ROOT)