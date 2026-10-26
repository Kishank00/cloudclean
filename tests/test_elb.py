from cloudclean.elb import count_targets, list_alb


class FakeELB:
    def __init__(self, target_groups, targets):
        self.target_groups = target_groups
        self.targets = targets

    def describe_target_groups(self, LoadBalancerArn):
        return {"TargetGroups": self.target_groups}

    def describe_target_health(self, TargetGroupArn):
        return {"TargetHealthDescriptions": self.targets}


def test_alb_with_no_target_group_has_zero_targets():
    elb = FakeELB(target_groups=[], targets=[])
    assert count_targets(elb, "arn:alb") == 0


def test_counts_targets():
    elb = FakeELB(
        target_groups=[{"TargetGroupArn": "arn:tg"}],
        targets=[{"Target": {"Id": "i-1"}}, {"Target": {"Id": "i-2"}}],
    )
    assert count_targets(elb, "arn:alb") == 2


def test_list_alb_saves_target_count():
    elb = FakeELB(target_groups=[], targets=[])
    response = {"LoadBalancers": [{"LoadBalancerArn": "arn:alb"}]}
    albs = list_alb(elb, response)
    assert albs[0]["TargetCount"] == 0
