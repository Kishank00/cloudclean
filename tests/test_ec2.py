from cloudclean.ec2 import (
    find_orphan_snapshots,
    find_unattached_eips,
    list_amis,
    list_instances,
)


# Fake paginator: returns the pages we give it, like the real one does
class FakePaginator:
    def __init__(self, pages):
        self.pages = pages

    def paginate(self, **kwargs):
        return self.pages


# Fake ec2 client: only the method list_amis needs
class FakeEC2:
    def describe_images(self, Owners):
        return {"Images": [{"ImageId": "ami-1", "Name": "test"}]}


def test_list_instances_reads_all_pages():
    pages = [
        {"Reservations": [{"Instances": [{"InstanceId": "i-1"}]}]},
        {"Reservations": [{"Instances": [{"InstanceId": "i-2"}]}]},
    ]
    instances = list_instances(FakePaginator(pages))
    assert [i["InstanceId"] for i in instances] == ["i-1", "i-2"]


def test_unattached_eips_skips_attached_ones():
    response = {
        "Addresses": [
            {"PublicIp": "1.1.1.1", "AssociationId": "eipassoc-1"},
            {"PublicIp": "2.2.2.2"},
        ]
    }
    eips = find_unattached_eips(response)
    assert [e["PublicIp"] for e in eips] == ["2.2.2.2"]


def test_list_amis():
    amis = list_amis(FakeEC2())
    assert amis[0]["ImageId"] == "ami-1"


def test_snapshot_used_by_ami_is_not_orphan():
    amis = [{"BlockDeviceMappings": [{"Ebs": {"SnapshotId": "snap-1"}}]}]
    snapshots = [{"SnapshotId": "snap-1"}]
    assert find_orphan_snapshots(amis, snapshots) == []


def test_snapshot_without_ami_is_orphan():
    snapshots = [{"SnapshotId": "snap-1"}]
    assert find_orphan_snapshots([], snapshots) == snapshots


def test_ephemeral_disks_are_ignored():
    amis = [
        {
            "BlockDeviceMappings": [
                {"Ebs": {"SnapshotId": "snap-1"}},
                {"DeviceName": "/dev/sdb", "VirtualName": "ephemeral0"},
            ]
        }
    ]
    assert find_orphan_snapshots(amis, [{"SnapshotId": "snap-1"}]) == []
