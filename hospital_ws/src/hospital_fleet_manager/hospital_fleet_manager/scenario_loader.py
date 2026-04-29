import os
from copy import deepcopy

import yaml


DEFAULT_SCENARIO = {
    "charging": {
        "stations": ["MainLobby", "ER", "Supply", "NursingStationE"],
        "dispatch_threshold": 28.0,
        "reject_below_percent": 18.0,
        "target_percent": 92.0,
        "energy_per_distance": 1.8,
        "reserve_percent": 12.0,
    },
    "sla": {
        "priority_rank": {"critical": 4, "high": 3, "medium": 2, "low": 1},
        "deadline_secs": {"critical": 40, "high": 90, "medium": 180, "low": 300},
        "preemptable_levels": ["low", "medium"],
    },
    "navigation": {
        "corridor_capacity": 3,
        "edge_over_capacity_penalty": 7.5,
        "floor_transfer_penalty": 4.0,
        "transfer_hubs": ["NursingStationE", "MainLobby"],
    },
}


def _default_scenario_path():
    return os.path.join(os.path.dirname(__file__), "config", "scenario_default.yaml")


def load_scenario(path=None):
    scenario_path = path or os.environ.get("HOSPITAL_SCENARIO_FILE") or _default_scenario_path()
    loaded = {}
    if os.path.exists(scenario_path):
        with open(scenario_path, "r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f) or {}

    merged = deepcopy(DEFAULT_SCENARIO)
    for key, value in loaded.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key].update(value)
        else:
            merged[key] = value
    merged["_scenario_path"] = scenario_path
    return merged
