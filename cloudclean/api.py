import boto3
from cloudclean.ec2 import list_instances

from fastapi import FastAPI

app = FastAPI()

session = boto3.Session(region_name="ap-south-1", profile_name="personal")
ec2 = session.client("ec2")


@app.get("/")
def home():
    return {"message": "Cloudclean is UP and running"}


@app.get("/instances")
def get_instances():
    paginator = ec2.get_paginator("describe_instances")
    return list_instances(paginator)
