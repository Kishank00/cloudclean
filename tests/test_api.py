import boto3
from fastapi.testclient import TestClient


class FakeEC2:
    def describe_images(self, Owners):
        return {"Images": [{"ImageId": "ami-1", "Name": "test"}]}


def test_api(monkeypatch):
    # api.py builds a boto3 session when imported; give it a fake one so
    # the test needs no AWS profile or network
    monkeypatch.setattr(boto3, "Session", lambda **kwargs: FakeSession())
    from cloudclean import api

    monkeypatch.setattr(api, "ec2", FakeEC2())
    client = TestClient(api.app)

    assert client.get("/").status_code == 200
    assert client.get("/amis").json()[0]["ImageId"] == "ami-1"
    assert client.get("/ecr-images?max_age=abc").status_code == 422


class FakeSession:
    def client(self, name):
        return object()
