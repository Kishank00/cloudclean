from cloudclean.pricing import calculate_cost


def test_nothing_found_costs_zero():
    cost = calculate_cost([], [], [], [], [], [])
    assert cost["total"] == 0


def test_one_t3_micro_costs_about_8_dollars():
    cost = calculate_cost([{"InstanceType": "t3.micro"}], [], [], [], [], [])
    assert round(cost["instances"], 2) == 8.18


def test_unknown_instance_type_costs_zero():
    cost = calculate_cost([{"InstanceType": "m5.24xlarge"}], [], [], [], [], [])
    assert cost["instances"] == 0


def test_orphan_snapshot_costs_5_cents_per_gb():
    cost = calculate_cost([], [], [], [], [], [{"VolumeSize": 8}])
    assert round(cost["orphan_snapshots"], 2) == 0.40


def test_total_adds_everything():
    cost = calculate_cost(
        [{"InstanceType": "t3.micro"}],
        [{"PublicIp": "1.2.3.4"}],
        [],
        [],
        [],
        [{"VolumeSize": 8}],
    )
    parts = cost["instances"] + cost["unattached_eips"] + cost["orphan_snapshots"]
    assert cost["total"] == parts
