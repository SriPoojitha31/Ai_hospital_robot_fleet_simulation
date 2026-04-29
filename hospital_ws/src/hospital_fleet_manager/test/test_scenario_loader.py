from hospital_fleet_manager.scenario_loader import load_scenario


def test_load_scenario_defaults():
    scenario = load_scenario()
    assert "charging" in scenario
    assert "sla" in scenario
    assert "navigation" in scenario
    assert isinstance(scenario.get("robots"), dict)
    assert isinstance(scenario.get("initial_tasks"), list)


def test_priority_rank_has_critical():
    scenario = load_scenario()
    assert scenario["sla"]["priority_rank"]["critical"] > scenario["sla"]["priority_rank"]["low"]
