[中文](README.md)
# Bedrock IP Restrict

Manage IP-restricted IAM users for AWS Bedrock inference access control. Creates an IAM user with AK/SK that can only call `InvokeModel` from specified source IPs, with Bedrock API Key creation explicitly denied.

## Prerequisites

- Python 3.10+
- boto3
- An AWS CLI profile with IAM management permissions

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install boto3
```

## Usage

```bash
PYTHON=.venv/bin/python3
```

### Create a restricted user

Creates IAM user `bedrock-ip-restricted`, attaches an IP-restricted policy, and generates AK/SK (shown only once).

```bash
$PYTHON bedrock_ip_restrict.py create --profile default --ips 1.2.3.4 5.6.7.8
```

### Show current configuration

Displays the current allowed IP list and Access Key info.

```bash
$PYTHON bedrock_ip_restrict.py show --profile default
```

### Update allowed IPs

Replaces the entire IP allowlist (full replacement, not append).

```bash
$PYTHON bedrock_ip_restrict.py update --profile default --ips 1.2.3.4 9.10.11.12
```

### Delete user and cleanup

Removes the IAM user, policy, and all Access Keys.

```bash
$PYTHON bedrock_ip_restrict.py delete --profile default
```

### Show test commands

Outputs sample aws cli commands for manual verification.

```bash
$PYTHON bedrock_ip_restrict.py test --profile default
```

## Using the generated AK/SK

After creation, pass credentials via environment variables to call Bedrock without modifying your `~/.aws` config:

```bash
AWS_ACCESS_KEY_ID=<key> \
AWS_SECRET_ACCESS_KEY=<secret> \
AWS_DEFAULT_REGION=us-east-1 \
aws bedrock-runtime invoke-model \
  --model-id anthropic.claude-sonnet-4-20250514-v1:0 \
  --content-type application/json --accept application/json \
  --body "$(echo -n '{"anthropic_version":"bedrock-2023-05-31","max_tokens":50,"messages":[{"role":"user","content":"hello"}]}' | base64)" \
  /dev/stdout
```

## IAM Policy Details

The generated policy contains two statements:

1. **Allow** `InvokeModel` + `InvokeModelWithResponseStream` — restricted by `aws:SourceIp` condition
2. **Deny** `iam:CreateServiceSpecificCredential` + `bedrock:CallWithBearerToken` — prevents creating or using Bedrock API Keys to bypass IP restrictions

## Important Notes

- **IAM policy is global** — one policy covers Bedrock calls across all Regions
- IP addresses are automatically suffixed with `/32`; CIDR notation is also supported (e.g., `10.0.0.0/24`)
- IAM policy propagation typically takes a few seconds to one minute — wait briefly after create/update before testing
- The policy only allows `InvokeModel` and `InvokeModelWithResponseStream`; control plane APIs like `ListFoundationModels` are not included

## Claude Code Skill

This tool is also available as a Claude Code skill. Copy the `SKILL.md` and `bedrock_ip_restrict.py` to `~/.claude/skills/bedrock-ip-restrict/` to use it via `/bedrock-ip-restrict` in Claude Code.
