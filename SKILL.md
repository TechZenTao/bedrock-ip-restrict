---
name: bedrock-ip-restrict
description: 管理 Bedrock 推理调用的源 IP 限制。创建/查看/更新/删除带 IP 白名单的 IAM 用户，限制只有指定源 IP 才能调用 InvokeModel。适用于需要对 AWS Bedrock 做 IP 访问控制的场景。
when_to_use: 当用户需要限制 Bedrock 调用的源 IP、创建带 IP 限制的 IAM 用户、管理 Bedrock IP 白名单时使用。
argument-hint: <action> --profile <profile> [--ips <ip1> <ip2> ...]
arguments: [action]
disable-model-invocation: true
allowed-tools: Bash(python *) Bash(pip *) Read
---

# Bedrock IP Restrict

通过 IAM 用户策略限制 Bedrock 推理调用（InvokeModel / InvokeModelWithResponseStream）的源 IP。

## 工作原理

- 创建专用 IAM 用户 `bedrock-ip-restricted`，附加带 `aws:SourceIp` 条件的 inline policy
- 生成 AK/SK 供调用方使用，通过环境变量传入，不影响本地 `~/.aws` 配置
- IAM 策略全局生效，覆盖所有 Region

## 执行步骤

1. 确认用户安装了 boto3，若没有则在项目目录创建 venv 安装
2. 找到脚本 `bedrock_ip_restrict.py`，若当前目录没有则从 `${CLAUDE_SKILL_DIR}/bedrock_ip_restrict.py` 复制到当前目录
3. 根据用户请求的操作执行对应命令：

### create — 创建受限用户

```bash
python bedrock_ip_restrict.py create --profile <profile> --ips <ip1> <ip2> ...
```

### show — 查看当前配置

```bash
python bedrock_ip_restrict.py show --profile <profile>
```

### update — 更新允许的 IP

```bash
python bedrock_ip_restrict.py update --profile <profile> --ips <ip1> <ip2> ...
```

### delete — 删除用户并清理

```bash
python bedrock_ip_restrict.py delete --profile <profile>
```

## 注意事项

- IAM 策略传播需要几秒到一分钟，创建/更新后稍等再测试
- IP 地址自动补全 `/32`，也支持 CIDR 格式（如 `10.0.0.0/24`）
- 策略中包含显式 Deny，禁止该 IAM 用户创建或使用 Bedrock API Key（`iam:CreateServiceSpecificCredential` 和 `bedrock:CallWithBearerToken`），防止绕过 IP 限制

## 如果用户没有指定参数

- 没有指定 profile：询问使用哪个 AWS CLI profile
- 没有指定 IP：询问要允许哪些源 IP，可以帮用户用 `curl -s https://checkip.amazonaws.com` 获取当前公网 IP 作为参考
- 没有指定操作：询问要执行什么操作（create/show/update/delete）
