from datetime import datetime, timedelta, timezone

from cloudclean.ecr import list_ecr


class FakeECR:
    def __init__(self, images):
        self.images = images

    def describe_repositories(self):
        return {"repositories": [{"repositoryName": "app"}]}

    def describe_images(self, repositoryName):
        return {"imageDetails": self.images}


def days_ago(n):
    return datetime.now(timezone.utc) - timedelta(days=n)


def test_only_old_images_are_returned():
    ecr = FakeECR(
        [
            {"imageDigest": "new", "imagePushedAt": days_ago(5)},
            {"imageDigest": "old", "imagePushedAt": days_ago(100)},
        ]
    )
    old = list_ecr(ecr, 90)
    assert [i["imageDigest"] for i in old] == ["old"]
    assert old[0]["AgeDays"] == 100
