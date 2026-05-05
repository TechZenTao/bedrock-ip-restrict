[English](README_en.md)      [Claude Skill](Skill.md)
# Bedrock IP Restrict

通过 IAM 用户策略限制 Bedrock 推理调用的源 IP，创建一个只能从指定 IP 调用 `InvokeModel` 的 IAM 用户及 AK/SK。

## 前置条件

- Python 3.10+
- boto3（已安装在 `.venv` 中）
- 具有 IAM 管理权限的 AWS CLI profile

## 安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install boto3
```

## 使用方式

```bash
PYTHON=.venv/bin/python3
```

### 创建受限用户

创建 IAM 用户 `bedrock-ip-restricted`，附加 IP 限制策略，并生成 AK/SK（仅显示一次）。

```bash
$PYTHON bedrock_ip_restrict.py create --profile default --ips 1.2.3.4 5.6.7.8
```

### 查看当前配置

查看已配置的允许 IP 列表和 Access Key 信息。

```bash
$PYTHON bedrock_ip_restrict.py show --profile default
```

### 更新允许的 IP

替换当前的 IP 白名单（全量替换，非追加）。

```bash
$PYTHON bedrock_ip_restrict.py update --profile default --ips 1.2.3.4 9.10.11.12
```

### 删除用户并清理

删除 IAM 用户、策略和所有 Access Key。

```bash
$PYTHON bedrock_ip_restrict.py delete --profile default
```

### 查看测试命令

输出用于手动验证的 aws cli 调用命令。

```bash
$PYTHON bedrock_ip_restrict.py test --profile default
```

## 使用生成的 AK/SK

创建成功后，通过环境变量传入凭证调用 Bedrock，不影响本地 `~/.aws` 配置：

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

## 注意事项

- **IAM 策略全局生效**，一条策略覆盖所有 Region 的 Bedrock 调用
- IP 地址会自动补全 `/32` 后缀，也支持直接传入 CIDR（如 `10.0.0.0/24`）
- IAM 策略传播通常需要几秒到一分钟，创建/更新后稍等片刻再测试
- 策略仅允许 `InvokeModel` 和 `InvokeModelWithResponseStream`，不包含 `ListFoundationModels` 等控制面 API
