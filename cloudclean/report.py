from cloudclean.pricing import (
    HOURS_PER_MONTH,
    EIP_HOURLY,
    NAT_HOURLY,
    ALB_HOURLY,
    SNAPSHOT_GB_MONTHLY,
    ECR_GB_MONTHLY,
    INSTANCE_HOURLY,
)


# Get names from the tag
def get_name(instance):
    tags = instance.get("Tags", [])
    for tag in tags:
        if tag["Key"] == "Name":
            return tag["Value"]

    return "Tag not found"


def print_instances(instances):
    print(f"{'INSTANCE ID':<20} {'STATE':<10} {'TYPE':<10} {'LAUNCHED':<16}  NAME")
    for instance in instances:
        print(
            f"{instance['InstanceId']:<20} "
            f"{instance['State']['Name']:<10} "
            f"{instance['InstanceType']:<10} "
            f"{instance['LaunchTime']:%Y-%m-%d %H:%M}  "
            f"{get_name(instance)}"
        )
    if len(instances) == 0:
        print("No running EC2 instances found")


def print_eips(eips):
    for address in eips:
        print(f"Unattached EIP: {address["PublicIp"]} {get_name(address)}")


def print_nat_gw(nat_gateways):
    print(f"{'NAT ID':<22} {'STATE':<10} {'VPC':<22} {'CREATED':<16}  NAME")
    for ngw in nat_gateways:
        print(
            f"{ngw['NatGatewayId']:<22} "
            f"{ngw['State']:<10} "
            f"{ngw['VpcId']:<22} "
            f"{ngw['CreateTime']:%Y-%m-%d %H:%M}  "
            f"{get_name(ngw)}"
        )
    if len(nat_gateways) == 0:
        print("No NAT Gateway Found")


def print_alb(albs):
    print(
        f"{'ALB NAME':<18} {'STATE':<8} {'TYPE':<12} {'VPC':<22} {'CREATED':<16}  TARGETS"
    )
    for lb in albs:
        print(
            f"{lb['LoadBalancerName']:<18} "
            f"{lb['State']['Code']:<8} "
            f"{lb['Type']:<12} "
            f"{lb['VpcId']:<22} "
            f"{lb['CreatedTime']:%Y-%m-%d %H:%M}  "
            f"{lb["TargetCount"]}"
        )
        if lb["TargetCount"] == 0:
            print(
                f"{lb['LoadBalancerName']} has no targets, it costs money but serves nothing"
            )

    if len(albs) == 0:
        print("No Load Balancers Found")


def print_ecr(images):
    print(f"{'REPOSITORY':<24} {'TAG':<14} {'PUSHED':<16}  {'AGE':<5} SIZE")
    for image in images:
        tag = image.get("imageTags", ["<untagged>"])[0][:12]
        print(
            f"{image['repositoryName']:<24} "
            f"{tag:<14} "
            f"{image['imagePushedAt']:%Y-%m-%d %H:%M}  "
            f"{str(image['AgeDays']) + 'd':<5} "
            f"{image['imageSizeInBytes'] / 1024 / 1024:.0f} MB"
        )
    if len(images) == 0:
        print("No old ECR images found")


def print_cost(instances, eips, nats, albs, images, orphans):
    print("=== ESTIMATED MONTHLY COST ===")
    instance_cost = 0
    for instance in instances:
        hourly = INSTANCE_HOURLY.get(instance["InstanceType"], 0)
        instance_cost += hourly * HOURS_PER_MONTH
    print(
        f"{'Running instances':<20} {len(instances):<10} {f'${instance_cost:.2f}':>9}"
    )

    eip_cost = len(eips) * HOURS_PER_MONTH * EIP_HOURLY
    print(f"{'Unattached EIPs':<20} {len(eips):<10} {f'${eip_cost:.2f}':>9}")

    nat_cost = len(nats) * HOURS_PER_MONTH * NAT_HOURLY
    print(f"{'NAT gateways':<20} {len(nats):<10} {f'${nat_cost:.2f}':>9}")

    alb_cost = len(albs) * HOURS_PER_MONTH * ALB_HOURLY
    print(f"{'Load balancers':<20} {len(albs):<10} {f'${alb_cost:.2f}':>9}")

    total_bytes = 0
    for image in images:
        total_bytes += image["imageSizeInBytes"]
    gb = total_bytes / (1024**3)
    ecr_cost = gb * ECR_GB_MONTHLY
    print(f"{'Old ECR images':<20} {f'{gb:.2f} GB':<10} {f'${ecr_cost:.2f}':>9}")

    snapshot_gb = 0
    for snap in orphans:
        snapshot_gb += snap["VolumeSize"]
    snapshot_cost = snapshot_gb * SNAPSHOT_GB_MONTHLY
    print(
        f"{'Orphan snapshots':<20} {f'{snapshot_gb} GB':<10} {f'${snapshot_cost:.2f}':>9}"
    )

    total = instance_cost + eip_cost + nat_cost + alb_cost + ecr_cost + snapshot_cost
    print("-" * 50)
    print(f"{'TOTAL':<31} {f'${total:.2f}':>9} / month")


def print_amis(amis):
    print(f"{'AMI ID':<22} {'CREATED':<16}  NAME")
    for image in amis:
        print(
            f"{image['ImageId']:<22} "
            f"{image['CreationDate'][:16]:<16}  "
            f"{image['Name']}"
        )
    if len(amis) == 0:
        print("No AMIs found")


def print_snapshots(snapshots):
    print(f"{'SNAPSHOT ID':<24} {'SIZE':<6} {'CREATED':<16}")
    for snap in snapshots:
        print(
            f"{snap['SnapshotId']:<24} "
            f"{str(snap['VolumeSize']) + ' GB':<6} "
            f"{snap['StartTime']:%Y-%m-%d %H:%M}"
        )
    if len(snapshots) == 0:
        print("No snapshots found")


def print_orphans(orphans):
    for snap in orphans:
        print(
            f"Orphan snapshot: {snap['SnapshotId']} ({snap['VolumeSize']} GB), no AMI uses it"
        )
    if len(orphans) == 0:
        print("No orphan snapshots found")
