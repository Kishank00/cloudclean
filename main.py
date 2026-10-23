import boto3


def main():
    session = boto3.Session(region_name="ap-south-1", profile_name="personal")
    ec2 = session.client("ec2")
    paginator = ec2.get_paginator("describe_instances")
    list_instances(paginator)


def get_name(instance):
    tags = instance.get("Tags", [])
    for tag in tags:
        if tag["Key"] == "Name":
            return tag["Value"]

    return "Tag not found"


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


if __name__ == "__main__":
    main()
