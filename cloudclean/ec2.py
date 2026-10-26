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


# Find Unattached ElasticIP's
def find_unattached_eips(elastic_ip):
    unattached = []
    for address in elastic_ip["Addresses"]:
        if not address.get("AssociationId"):
            unattached.append(address)

    return unattached


def list_nat_gw(nat_gw_paginator):
    pages = nat_gw_paginator.paginate(
        Filters=[{"Name": "state", "Values": ["available"]}]
    )

    nat_gateways = []
    for page in pages:
        for ngw in page["NatGateways"]:
            nat_gateways.append(ngw)

    return nat_gateways


def list_amis(ec2):
    response = ec2.describe_images(
        Owners=["self"],
    )

    amis = []
    for image in response["Images"]:
        amis.append(image)

    return amis


def list_snapshots(ec2):
    response = ec2.describe_snapshots(
        OwnerIds=["self"],
    )
    snapshots = []
    for snap in response["Snapshots"]:
        snapshots.append(snap)

    return snapshots


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
