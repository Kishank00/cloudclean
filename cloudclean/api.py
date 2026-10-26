import boto3
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

from fastapi import FastAPI

app = FastAPI()

session = boto3.Session(region_name="ap-south-1", profile_name="personal")
ec2 = session.client("ec2")
elb = session.client("elbv2")
ecr = session.client("ecr")


@app.get("/")
def home():
    return {"message": "Cloudclean is UP and running"}


@app.get("/instances")
def get_instances():
    paginator = ec2.get_paginator("describe_instances")
    return list_instances(paginator)


@app.get("/eips")
def get_eips():
    elastic_ip = ec2.describe_addresses()
    return find_unattached_eips(elastic_ip)


@app.get("/nat-gateways")
def get_ngw():
    nat = ec2.get_paginator("describe_nat_gateways")
    return list_nat_gw(nat)


@app.get("/amis")
def get_amis():
    return list_amis(ec2)


@app.get("/snapshots")
def get_snapshots():
    return list_snapshots(ec2)


@app.get("/orphan-snapshots")
def get_orphan_snapshots():
    amis = list_amis(ec2)
    snapshots = list_snapshots(ec2)
    return find_orphan_snapshots(amis, snapshots)


@app.get("/load-balancers")
def get_load_balancers():
    alb = elb.describe_load_balancers()
    return list_alb(elb, alb)


@app.get("/ecr-images")
def get_ecr_images(max_age: int = 90):
    return list_ecr(ecr, max_age)
