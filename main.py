import argparse
import boto3
import json
from datetime import datetime, timezone
from cloudclean.pricing import (
    HOURS_PER_MONTH,
    EIP_HOURLY,
    NAT_HOURLY,
    ALB_HOURLY,
    SNAPSHOT_GB_MONTHLY,
    ECR_GB_MONTHLY,
    INSTANCE_HOURLY,
)


def main():
    parser = argparse.ArgumentParser(
        description="Find forgotten AWS resources that cost money"
    )
    parser.add_argument("--region", default="ap-south-1", help="AWS region to scan")
    parser.add_argument("--profile", default="personal", help="AWS CLI profile to use")
    parser.add_argument(
        "--max-age",
        type=int,
        default=90,
        help="flag ECR images older than this many days",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print results as JSON instead of tables",
    )
    args = parser.parse_args()

    session = boto3.Session(region_name=args.region, profile_name=args.profile)
    ec2 = session.client("ec2")
    elb = session.client("elbv2")
    elastic_ip = ec2.describe_addresses()
    alb = elb.describe_load_balancers()
    ecr = session.client("ecr")

    nat_gw_paginator = ec2.get_paginator("describe_nat_gateways")
    paginator = ec2.get_paginator("describe_instances")

    # find
    instances = list_instances(paginator)
    eips = find_unattached_eips(elastic_ip)
    nats = list_nat_gw(nat_gw_paginator)
    albs = list_alb(elb, alb)
    images = list_ecr(ecr, args.max_age)
    amis = list_amis(ec2)
    snapshots = list_snapshots(ec2)
    orphans = find_orphan_snapshots(amis, snapshots)

    # print
    if args.json:
        result = {
            "instances": instances,
            "unattached_eips": eips,
            "nat_gateways": nats,
            "load_balancers": albs,
            "old_ecr_images": images,
            "amis": amis,
            "snapshots": snapshots,
            "orphan_snapshots": orphans,
        }
        print(json.dumps(result, default=str, indent=2))
    else:
        print_instances(instances)
        print_eips(eips)
        print_nat_gw(nats)
        print_alb(albs)
        print_ecr(images)
        print_amis(amis)
        print_snapshots(snapshots)
        print_orphans(orphans)
        print_cost(instances, eips, nats, albs, images, orphans)


# Get names from the tag
def get_name(instance):
    tags = instance.get("Tags", [])
    for tag in tags:
        if tag["Key"] == "Name":
            return tag["Value"]

    return "Tag not found"


# Listing running instances
def list_instances(paginator):
    pages = paginator.paginate(
        Filters=[
            {
                "Name": "instance-state-name",
                "Values": ["running"],
            }
        ]
    )
    running = []
    for page in pages:
        for reservation in page["Reservations"]:
            for instance in reservation["Instances"]:
                running.append(instance)

    return running


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


# Find Unattached ElasticIP's
def find_unattached_eips(elastic_ip):
    unattached = []
    for address in elastic_ip["Addresses"]:
        if not address.get("AssociationId"):
            unattached.append(address)

    return unattached


def print_eips(eips):
    for address in eips:
        print(f"Unattached EIP: {address["PublicIp"]} {get_name(address)}")


def list_nat_gw(nat_gw_paginator):
    pages = nat_gw_paginator.paginate(
        Filters=[{"Name": "state", "Values": ["available"]}]
    )

    nat_gateways = []
    for page in pages:
        for ngw in page["NatGateways"]:
            nat_gateways.append(ngw)

    return nat_gateways


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


def list_alb(elb, alb):
    load_balancer = []

    for lb in alb["LoadBalancers"]:
        load_balancer.append(lb)
        lb["TargetCount"] = count_targets(elb, lb["LoadBalancerArn"])

    return load_balancer


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


def count_targets(elb, alb_arn):

    tg_response = elb.describe_target_groups(LoadBalancerArn=alb_arn)
    if len(tg_response["TargetGroups"]) == 0:
        return 0
    tg_arn = tg_response["TargetGroups"][0]["TargetGroupArn"]

    tg_health = elb.describe_target_health(TargetGroupArn=tg_arn)
    return len(tg_health["TargetHealthDescriptions"])


def list_ecr(ecr, max_age_days):
    now = datetime.now(timezone.utc)
    old_images = []
    response = ecr.describe_repositories()
    for repo in response["repositories"]:
        images = ecr.describe_images(repositoryName=repo["repositoryName"])
        for image in images["imageDetails"]:
            age = (now - image["imagePushedAt"]).days
            image["AgeDays"] = age

            if age > max_age_days:
                old_images.append(image)

    return old_images


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


def list_amis(ec2):
    response = ec2.describe_images(
        Owners=["self"],
    )

    amis = []
    for image in response["Images"]:
        amis.append(image)

    return amis


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


def list_snapshots(ec2):
    response = ec2.describe_snapshots(
        OwnerIds=["self"],
    )
    snapshots = []
    for snap in response["Snapshots"]:
        snapshots.append(snap)

    return snapshots


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


def find_orphan_snapshots(amis, snapshots):
    used = set()
    for image in amis:
        for mapping in image["BlockDeviceMappings"]:
            if "Ebs" in mapping:
                used.add(mapping["Ebs"]["SnapshotId"])

    orphans = []
    for snap in snapshots:
        if snap["SnapshotId"] not in used:
            orphans.append(snap)

    return orphans


def print_orphans(orphans):
    for snap in orphans:
        print(
            f"Orphan snapshot: {snap['SnapshotId']} ({snap['VolumeSize']} GB), no AMI uses it"
        )
    if len(orphans) == 0:
        print("No orphan snapshots found")


if __name__ == "__main__":
    main()
