HOURS_PER_MONTH = 730

# Approximate ap-south-1 prices, USD per hour
EIP_HOURLY = 0.005
NAT_HOURLY = 0.056
ALB_HOURLY = 0.0239
SNAPSHOT_GB_MONTHLY = 0.05
ECR_GB_MONTHLY = 0.10
INSTANCE_HOURLY = {
    "t3.micro": 0.0112,
    "t3.small": 0.0224,
    "t3.medium": 0.0448,
}


def calculate_cost(instances, eips, nats, albs, images, orphans):
    instance_cost = 0
    for instance in instances:
        hourly = INSTANCE_HOURLY.get(instance["InstanceType"], 0)
        instance_cost += hourly * HOURS_PER_MONTH

    eip_cost = len(eips) * HOURS_PER_MONTH * EIP_HOURLY
    nat_cost = len(nats) * HOURS_PER_MONTH * NAT_HOURLY
    alb_cost = len(albs) * HOURS_PER_MONTH * ALB_HOURLY

    total_bytes = 0
    for image in images:
        total_bytes += image["imageSizeInBytes"]
    gb = total_bytes / (1024**3)
    ecr_cost = gb * ECR_GB_MONTHLY

    snapshot_gb = 0
    for snap in orphans:
        snapshot_gb += snap["VolumeSize"]
    snapshot_cost = snapshot_gb * SNAPSHOT_GB_MONTHLY

    total = instance_cost + eip_cost + nat_cost + alb_cost + ecr_cost + snapshot_cost

    return {
        "instances": instance_cost,
        "unattached_eips": eip_cost,
        "nat_gateways": nat_cost,
        "load_balancers": alb_cost,
        "old_ecr_images": ecr_cost,
        "orphan_snapshots": snapshot_cost,
        "total": total,
    }
