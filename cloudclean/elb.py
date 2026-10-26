def list_alb(elb, alb):
    load_balancer = []

    for lb in alb["LoadBalancers"]:
        load_balancer.append(lb)
        lb["TargetCount"] = count_targets(elb, lb["LoadBalancerArn"])

    return load_balancer


def count_targets(elb, alb_arn):

    tg_response = elb.describe_target_groups(LoadBalancerArn=alb_arn)
    if len(tg_response["TargetGroups"]) == 0:
        return 0
    tg_arn = tg_response["TargetGroups"][0]["TargetGroupArn"]

    tg_health = elb.describe_target_health(TargetGroupArn=tg_arn)
    return len(tg_health["TargetHealthDescriptions"])
