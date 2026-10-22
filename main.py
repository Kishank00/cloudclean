import boto3

session = boto3.Session(region_name="ap-south-1", profile_name="personal")

ec2 = session.client("ec2")


def get_name(instance):
    tags = instance.get("Tags", [])
    for tag in tags:
        if tag["Key"] == "Name":
            return tag["Value"]

    return "Tag not found"


def list_instances():
    response = ec2.describe_instances()
    for reservation in response["Reservations"]:
        for instance in reservation["Instances"]:
            print(
                f"InstanceID: {instance['InstanceId']}, State: {instance['State']['Name']}, InstanceType: {instance['InstanceType']}, LaunchTime: {instance['LaunchTime']}, Name: {get_name(instance)}"
            )


list_instances()
