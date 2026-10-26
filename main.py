import argparse
import boto3
import json
from cloudclean.ec2 import (
    list_instances,
    find_unattached_eips,
    list_nat_gw,
    list_amis,
    list_snapshots,
    find_orphan_snapshots,
)
from cloudclean.elb import list_alb
from cloudclean.ecr import list_ecr
from cloudclean.report import (
    print_instances,
    print_eips,
    print_nat_gw,
    print_alb,
    print_ecr,
    print_cost,
    print_amis,
    print_snapshots,
    print_orphans,
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


if __name__ == "__main__":
    main()
