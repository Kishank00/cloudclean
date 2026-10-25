# CloudClean

A small Python CLI that scans an AWS account for forgotten resources that keep costing money, and estimates the monthly bill for them.

Built with [boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html). It only makes read-only `describe_*` calls and never deletes anything.

## What it finds

- **Running EC2 instances**: ID, type, launch time and Name tag
- **Unattached Elastic IPs**: allocated but not associated with anything
- **NAT gateways**: every available NAT gateway, which costs money by the hour
- **Application Load Balancers**: with a warning when an ALB has no registered targets
- **Old ECR images**: images older than `--max-age` days, with their size
- **Estimated monthly cost**: per resource type and a total

## How to run

Requirements: Python 3.13+, [uv](https://docs.astral.sh/uv/) and an AWS CLI profile with read access.

```bash
git clone https://github.com/Kishank00/cloudclean.git
cd cloudclean
uv sync
uv run python main.py
```

Flags:

| Flag | Default | Meaning |
|------|---------|---------|
| `--region` | `ap-south-1` | AWS region to scan |
| `--profile` | `personal` | AWS CLI profile to use |
| `--max-age` | `90` | Flag ECR images older than this many days |

Example:

```bash
uv run python main.py --region ap-south-1 --profile personal --max-age 30
```

## Example output

```
INSTANCE ID          STATE      TYPE       LAUNCHED          NAME
No running EC2 instances found
NAT ID                 STATE      VPC                    CREATED           NAME
No NAT Gateway Found
ALB NAME           STATE    TYPE         VPC                    CREATED           TARGETS
No Load Balancers Found
REPOSITORY               TAG            PUSHED            AGE   SIZE
linux-diagnostic-tool    cb41edbbcd89   2026-10-22 01:20  3d    206 MB
linux-diagnostic-tool    383aef87ffdb   2026-10-21 23:11  3d    206 MB
linux-diagnostic-tool    33413c36d9bc   2026-10-22 00:33  3d    206 MB
=== ESTIMATED MONTHLY COST ===
Running instances    0              $0.00
Unattached EIPs      0              $0.00
NAT gateways         0              $0.00
Load balancers       0              $0.00
Old ECR images       0.60 GB        $0.06
--------------------------------------------------
TOTAL                               $0.06 / month
```

## Notes

- Prices are approximate on-demand rates for `ap-south-1`. Other regions will show the same numbers.
- Only `t3.micro`, `t3.small` and `t3.medium` have instance prices; other types count as $0.

## Roadmap

- Orphaned AMIs and EBS snapshots
- Count only healthy targets on load balancers
- `--json` output and install as a `cloudclean` command
- Tests with mocked boto3
- FastAPI endpoints
