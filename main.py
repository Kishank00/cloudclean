import boto3


def main():
    session = boto3.Session(region_name="ap-south-1", profile_name="personal")
    ec2 = session.client("ec2")
    elb = session.client("elbv2")
    elastic_ip = ec2.describe_addresses()
    alb = elb.describe_load_balancers()

    nat_gw_paginator = ec2.get_paginator("describe_nat_gateways")
    paginator = ec2.get_paginator("describe_instances")
    list_instances(paginator)
    find_unattached_eips(elastic_ip)
    list_nat_gw(nat_gw_paginator)
    list_alb(alb)


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


def list_alb(alb):
    print(f"{'ALB NAME':<18} {'STATE':<8} {'TYPE':<12} {'VPC':<22} CREATED")

    load_balancer = []

    for lb in alb["LoadBalancers"]:
        load_balancer.append(lb)
        print(
            f"{lb['LoadBalancerName']:<18} "
            f"{lb['State']['Code']:<8} "
            f"{lb['Type']:<12} "
            f"{lb['VpcId']:<22} "
            f"{lb['CreatedTime']:%Y-%m-%d %H:%M}"
        )

    if len(load_balancer) == 0:
        print("No Load Balancers Found")


if __name__ == "__main__":
    main()
