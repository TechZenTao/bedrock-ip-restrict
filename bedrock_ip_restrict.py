#!/usr/bin/env python3
"""
Bedrock InvokeModel IP restriction tool.

Creates an IAM user with AK/SK that can only call Bedrock runtime APIs
from specified source IPs.

Usage:
  # Create restricted user
  python bedrock_ip_restrict.py create --profile default --ips 1.2.3.4 5.6.7.8

  # Show current config
  python bedrock_ip_restrict.py show --profile default

  # Update allowed IPs
  python bedrock_ip_restrict.py update --profile default --ips 1.2.3.4 9.10.11.12

  # Delete user and cleanup
  python bedrock_ip_restrict.py delete --profile default

  # Test access
  python bedrock_ip_restrict.py test --profile default
"""

import argparse
import json
import sys

import boto3
from botocore.exceptions import ClientError

USER_NAME = "bedrock-ip-restricted"
POLICY_NAME = "bedrock-ip-restrict"


def get_session(profile: str) -> boto3.Session:
    return boto3.Session(profile_name=profile)


def build_policy(ips: list[str]) -> str:
    cidrs = [ip if "/" in ip else f"{ip}/32" for ip in ips]
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowBedrockInvokeFromAllowedIPs",
                "Effect": "Allow",
                "Action": [
                    "bedrock-runtime:InvokeModel",
                    "bedrock-runtime:InvokeModelWithResponseStream",
                ],
                "Resource": "*",
                "Condition": {
                    "IpAddress": {"aws:SourceIp": cidrs}
                },
            },
            {
                "Sid": "DenyBedrockApiKeyCreationAndUsage",
                "Effect": "Deny",
                "Action": [
                    "iam:CreateServiceSpecificCredential",
                    "bedrock:CallWithBearerToken",
                ],
                "Resource": "*",
            },
        ],
    }
    return json.dumps(policy)


def cmd_create(args):
    session = get_session(args.profile)
    iam = session.client("iam")

    try:
        iam.create_user(UserName=USER_NAME)
        print(f"Created IAM user: {USER_NAME}")
    except ClientError as e:
        if e.response["Error"]["Code"] == "EntityAlreadyExists":
            print(f"IAM user {USER_NAME} already exists, updating policy.")
        else:
            raise

    policy_doc = build_policy(args.ips)
    iam.put_user_policy(
        UserName=USER_NAME,
        PolicyName=POLICY_NAME,
        PolicyDocument=policy_doc,
    )
    print(f"Attached IP-restricted policy. Allowed IPs: {args.ips}")

    try:
        resp = iam.create_access_key(UserName=USER_NAME)
        ak = resp["AccessKey"]
        print()
        print("=" * 60)
        print("ACCESS KEY CREATED (save these, shown only once)")
        print("=" * 60)
        print(f"  AWS_ACCESS_KEY_ID     = {ak['AccessKeyId']}")
        print(f"  AWS_SECRET_ACCESS_KEY = {ak['SecretAccessKey']}")
        print("=" * 60)
    except ClientError as e:
        if e.response["Error"]["Code"] == "LimitExceeded":
            print("\nAccess key limit reached. Use 'show' to see existing keys,")
            print("or 'delete' then re-create.")
        else:
            raise


def cmd_show(args):
    session = get_session(args.profile)
    iam = session.client("iam")

    try:
        iam.get_user(UserName=USER_NAME)
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchEntity":
            print(f"User {USER_NAME} does not exist. Run 'create' first.")
            return
        raise

    try:
        resp = iam.get_user_policy(UserName=USER_NAME, PolicyName=POLICY_NAME)
        doc = resp["PolicyDocument"]
        policy = json.loads(doc) if isinstance(doc, str) else doc
        for stmt in policy.get("Statement", []):
            cidrs = stmt.get("Condition", {}).get("IpAddress", {}).get("aws:SourceIp", [])
            if isinstance(cidrs, str):
                cidrs = [cidrs]
            print(f"Allowed IPs: {cidrs}")
            print(f"Actions:     {stmt.get('Action', [])}")
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchEntity":
            print("No IP-restrict policy found.")
        else:
            raise

    resp = iam.list_access_keys(UserName=USER_NAME)
    keys = resp.get("AccessKeyMetadata", [])
    if keys:
        print(f"\nAccess keys ({len(keys)}):")
        for k in keys:
            print(f"  {k['AccessKeyId']}  Status={k['Status']}  Created={k['CreateDate']}")
    else:
        print("\nNo access keys.")


def cmd_update(args):
    session = get_session(args.profile)
    iam = session.client("iam")

    try:
        iam.get_user(UserName=USER_NAME)
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchEntity":
            print(f"User {USER_NAME} does not exist. Run 'create' first.")
            return
        raise

    policy_doc = build_policy(args.ips)
    iam.put_user_policy(
        UserName=USER_NAME,
        PolicyName=POLICY_NAME,
        PolicyDocument=policy_doc,
    )
    print(f"Updated allowed IPs: {args.ips}")


def cmd_delete(args):
    session = get_session(args.profile)
    iam = session.client("iam")

    try:
        iam.get_user(UserName=USER_NAME)
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchEntity":
            print(f"User {USER_NAME} does not exist. Nothing to delete.")
            return
        raise

    resp = iam.list_access_keys(UserName=USER_NAME)
    for k in resp.get("AccessKeyMetadata", []):
        iam.delete_access_key(UserName=USER_NAME, AccessKeyId=k["AccessKeyId"])
        print(f"Deleted access key: {k['AccessKeyId']}")

    try:
        iam.delete_user_policy(UserName=USER_NAME, PolicyName=POLICY_NAME)
        print(f"Deleted policy: {POLICY_NAME}")
    except ClientError:
        pass

    iam.delete_user(UserName=USER_NAME)
    print(f"Deleted IAM user: {USER_NAME}")


def cmd_test(args):
    session = get_session(args.profile)
    iam = session.client("iam")

    resp = iam.list_access_keys(UserName=USER_NAME)
    keys = [k for k in resp.get("AccessKeyMetadata", []) if k["Status"] == "Active"]
    if not keys:
        print("No active access keys. Run 'create' first.")
        return

    print("Testing with the restricted user's credentials...")
    print("(Using the existing AK/SK — you need to export them as env vars)")
    print()
    print("Run this to test:")
    print(f"  AWS_ACCESS_KEY_ID=<key> \\")
    print(f"  AWS_SECRET_ACCESS_KEY=<secret> \\")
    print(f"  AWS_DEFAULT_REGION=us-east-1 \\")
    print(f'  aws bedrock-runtime invoke-model \\')
    print(f'    --model-id anthropic.claude-sonnet-4-20250514-v1:0 \\')
    print(f'    --content-type application/json --accept application/json \\')
    print(f'    --body "$(echo -n \'{{"anthropic_version":"bedrock-2023-05-31","max_tokens":50,"messages":[{{"role":"user","content":"hello"}}]}}\' | base64)" \\')
    print(f"    /dev/stdout")


def main():
    parser = argparse.ArgumentParser(
        description="Manage IP-restricted Bedrock IAM user"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_create = sub.add_parser("create", help="Create user with IP restriction")
    p_create.add_argument("--profile", required=True, help="AWS CLI profile")
    p_create.add_argument("--ips", nargs="+", required=True, help="Allowed source IPs")

    p_show = sub.add_parser("show", help="Show current config")
    p_show.add_argument("--profile", required=True, help="AWS CLI profile")

    p_update = sub.add_parser("update", help="Update allowed IPs")
    p_update.add_argument("--profile", required=True, help="AWS CLI profile")
    p_update.add_argument("--ips", nargs="+", required=True, help="New allowed IPs")

    p_delete = sub.add_parser("delete", help="Delete user and cleanup")
    p_delete.add_argument("--profile", required=True, help="AWS CLI profile")

    p_test = sub.add_parser("test", help="Show test commands")
    p_test.add_argument("--profile", required=True, help="AWS CLI profile")

    args = parser.parse_args()
    {"create": cmd_create, "show": cmd_show, "update": cmd_update,
     "delete": cmd_delete, "test": cmd_test}[args.command](args)


if __name__ == "__main__":
    main()
