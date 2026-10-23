import boto3
from datetime import datetime, timezone


def main():
    session = boto3.Session(region_name="ap-south-1", profile_name="personal")
    ec2 = session.client("ec2")
    elb = session.client("elbv2")
    elastic_ip = ec2.describe_addresses()
    alb = elb.describe_load_balancers()
    ecr = session.client("ecr")

    nat_gw_paginator = ec2.get_paginator("describe_nat_gateways")
    paginator = ec2.get_paginator("describe_instances")
    list_instances(paginator)
    find_unattached_eips(elastic_ip)
    list_nat_gw(nat_gw_paginator)
    list_alb(elb, alb)
    list_ecr(ecr, 1)


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
    ec2_count = 0
    print(f"{'INSTANCE ID':<20} {'STATE':<10} {'TYPE':<10} {'LAUNCHED':<16}  NAME")
    for page in pages:
        for reservation in page["Reservations"]:
            for instance in reservation["Instances"]:
                print(
                    f"{instance['InstanceId']:<20} "
                    f"{instance['State']['Name']:<10} "
                    f"{instance['InstanceType']:<10} "
                    f"{instance['LaunchTime']:%Y-%m-%d %H:%M}  "
                    f"{get_name(instance)}"
                )
                ec2_count += 1
    if ec2_count == 0:
        print("No running EC2 instances in ap-south-1")


# Find Unattached ElasticIP's
def find_unattached_eips(elastic_ip):
    for address in elastic_ip["Addresses"]:
        if not address.get("AssociationId"):
            print(f"Unattached EIP: {address["PublicIp"]} {get_name(address)}")


def list_nat_gw(nat_gw_paginator):
    pages = nat_gw_paginator.paginate(
        Filters=[{"Name": "state", "Values": ["available"]}]
    )
    print(f"{'NAT ID':<22} {'STATE':<10} {'VPC':<22} {'CREATED':<16}  NAME")

    nat_gateways = []
    for page in pages:
        for ngw in page["NatGateways"]:
            nat_gateways.append(ngw)
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
    print(
        f"{'ALB NAME':<18} {'STATE':<8} {'TYPE':<12} {'VPC':<22} {'CREATED':<16}  TARGETS"
    )

    load_balancer = []

    for lb in alb["LoadBalancers"]:
        load_balancer.append(lb)
        targets = count_targets(elb, lb["LoadBalancerArn"])

        print(
            f"{lb['LoadBalancerName']:<18} "
            f"{lb['State']['Code']:<8} "
            f"{lb['Type']:<12} "
            f"{lb['VpcId']:<22} "
            f"{lb['CreatedTime']:%Y-%m-%d %H:%M}  "
            f"{targets}"
        )

        if targets == 0:
            print(
                f"{lb['LoadBalancerName']} has no targets, it costs money but serves nothing"
            )

    if len(load_balancer) == 0:
        print("No Load Balancers Found")


def count_targets(elb, alb_arn):

    tg_response = elb.describe_target_groups(LoadBalancerArn=alb_arn)
    tg_arn = tg_response["TargetGroups"][0]["TargetGroupArn"]

    tg_health = elb.describe_target_health(TargetGroupArn=tg_arn)
    return len(tg_health["TargetHealthDescriptions"])


def list_ecr(ecr, max_age_days):
    now = datetime.now(timezone.utc)
    print(f"{'REPOSITORY':<24} {'TAG':<14} {'PUSHED':<16}  {'AGE':<5} SIZE")
    old_images = []
    response = ecr.describe_repositories()
    for repo in response["repositories"]:
        images = ecr.describe_images(repositoryName=repo["repositoryName"])
        for image in images["imageDetails"]:
            age = (now - image["imagePushedAt"]).days

            if age > max_age_days:
                old_images.append(image)
                tag =image.get("imageTags", ["<untagged>"])[0][:12]
                print(
                    f"{repo['repositoryName']:<24} "
                    f"{tag:<14} "
                    f"{image['imagePushedAt']:%Y-%m-%d %H:%M}  "
                    f"{str(age) + 'd':<5} "
                    f"{image['imageSizeInBytes'] / 1024 / 1024:.0f} MB"
                )

    if len(old_images) == 0:
        print("No old ECR images found")


if __name__ == "__main__":
    main()
