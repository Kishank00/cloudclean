# CloudClean

Finds forgotten AWS resources that keep costing money, and estimates the monthly bill for them. Use it as a CLI or as a local web API.

Built with [boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html) and [FastAPI](https://fastapi.tiangolo.com/). It only makes read-only `describe_*` calls and never deletes anything.

## What it finds

| Check | Why it costs money |
|-------|--------------------|
| Running EC2 instances | billed every hour they run |
| Unattached Elastic IPs | AWS charges for public IPv4 addresses that are allocated but unused |
| NAT gateways | billed every hour, even with no traffic |
| Application Load Balancers | billed every hour; flagged when they have no target group or no targets |
| Old ECR images | storage for images older than `--max-age` days |
| Orphaned EBS snapshots | snapshots that no AMI uses any more, e.g. left behind after an AMI was deregistered |

It also lists your own AMIs and snapshots, and prints an **estimated monthly cost** per resource type plus a total.

## Setup

Requirements: Python 3.13+, [uv](https://docs.astral.sh/uv/) and an AWS CLI profile with read access.

```bash
git clone https://github.com/Kishank00/cloudclean.git
cd cloudclean
uv sync
```

## CLI

```bash
uv run python main.py
```

| Flag | Default | Meaning |
|------|---------|---------|
| `--region` | `ap-south-1` | AWS region to scan |
| `--profile` | `personal` | AWS CLI profile to use |
| `--max-age` | `90` | Flag ECR images older than this many days |
| `--json` | off | Print all results as one JSON object instead of tables |

Examples:

```bash
uv run python main.py --region us-east-1 --profile dev --max-age 30
uv run python main.py --json | jq '.orphan_snapshots[].SnapshotId'
```

### Example output

```
INSTANCE ID          STATE      TYPE       LAUNCHED          NAME
No running EC2 instances found
NAT ID                 STATE      VPC                    CREATED           NAME
No NAT Gateway Found
ALB NAME           STATE    TYPE         VPC                    CREATED           TARGETS
No Load Balancers Found
REPOSITORY               TAG            PUSHED            AGE   SIZE
linux-diagnostic-tool    cb41edbbcd89   2026-10-22 01:20  4d    206 MB
linux-diagnostic-tool    383aef87ffdb   2026-10-21 23:11  4d    206 MB
linux-diagnostic-tool    33413c36d9bc   2026-10-22 00:33  4d    206 MB
AMI ID                 CREATED           NAME
ami-0a1cc69a9d948cf53  2026-10-24T18:45  sysdiag-base-20261024-1840
SNAPSHOT ID              SIZE   CREATED
snap-090275dd643bd2b1d   8 GB   2026-10-24 18:45
No orphan snapshots found
=== ESTIMATED MONTHLY COST ===
Running instances    0              $0.00
Unattached EIPs      0              $0.00
NAT gateways         0              $0.00
Load balancers       0              $0.00
Old ECR images       0.60 GB        $0.06
Orphan snapshots     0 GB           $0.00
--------------------------------------------------
TOTAL                               $0.06 / month
```

## Web API

```bash
uv run fastapi dev cloudclean/api.py
```

Then open http://127.0.0.1:8000/docs for interactive docs.

| Endpoint | Returns |
|----------|---------|
| `GET /` | health check |
| `GET /instances` | running EC2 instances |
| `GET /eips` | unattached Elastic IPs |
| `GET /nat-gateways` | available NAT gateways |
| `GET /load-balancers` | load balancers with a `TargetCount` field |
| `GET /ecr-images?max_age=90` | ECR images older than `max_age` days |
| `GET /amis` | AMIs owned by the account |
| `GET /snapshots` | EBS snapshots owned by the account |
| `GET /orphan-snapshots` | snapshots no AMI uses |
| `GET /cost?max_age=90` | estimated monthly cost per type and total |

The API uses the `personal` profile in `ap-south-1` and has **no authentication**. Run it on localhost only.

## Project layout

```
main.py                 CLI: flags, then find, then print tables or JSON
cloudclean/
  ec2.py                instances, EIPs, NAT gateways, AMIs, snapshots, orphan check
  elb.py                load balancers and target counts
  ecr.py                old ECR images
  pricing.py            prices and calculate_cost()
  report.py             table output for the CLI
  api.py                FastAPI app
tests/                  pytest tests with fake AWS clients
```

Finding and printing are kept separate: every `list_*` function only returns data, so the CLI, the JSON output and the API all reuse the same code.

## Tests

```bash
uv run pytest -v
```

The tests use small fake AWS clients, so they need no AWS account or network.

## IAM permissions

Read-only access is enough:

```
ec2:DescribeInstances, ec2:DescribeAddresses, ec2:DescribeNatGateways,
ec2:DescribeImages, ec2:DescribeSnapshots,
elasticloadbalancing:DescribeLoadBalancers, elasticloadbalancing:DescribeTargetGroups,
elasticloadbalancing:DescribeTargetHealth,
ecr:DescribeRepositories, ecr:DescribeImages
```

## Notes

- Prices are approximate on-demand rates for `ap-south-1`; other regions show the same numbers.
- Only `t3.micro`, `t3.small` and `t3.medium` have instance prices; other types count as $0.
- Snapshot cost uses the full volume size, so it is an upper bound (AWS bills only changed blocks).
- The load balancer cost counts every ALB, not only unused ones.

## Roadmap

- Scan all regions in one run
- Unattached EBS volumes
- Load balancers with zero requests (CloudWatch `RequestCount`)
- Install as a `cloudclean` command
- GitHub Actions workflow to run the tests
