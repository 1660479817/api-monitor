# api-monitor

轻量级命令行工具，用于批量检测多个 AI 平台的 API Key 是否可用。

## 功能

- 从 `config.yaml` 读取多个平台、多个 API Key
- 每个 Key 支持 `alias` 别名，并可配置多个待测 `models`
- 检测流程：**先 `GET /models` 验证 Key 并获取模型列表，再对每个目标模型发送极短 chat 请求**（`max_tokens: 1`，prompt 仅 `"1"`，几乎不消耗 token）
- 未配置 `models` 时，自动从 `/models` 返回列表中取前 `max_auto_models` 个进行探测
- 并发检测，并发数可配置
- 终端 Rich 表格输出，或 JSON 格式输出
- API Key 自动脱敏，不会完整打印到日志或终端

## 支持的平台

每个 Key 的检测均为两步：**① 拉取模型列表 → ② 逐模型 chat 探测**。


| 平台            | 配置名                 | ① 获取模型               | ② 模型探测                                    |
| ------------- | ------------------- | -------------------- | ----------------------------------------- |
| OpenAI        | `openai`            | `GET /models`        | `POST /chat/completions`                  |
| OpenAI 兼容中转   | `openai-compatible` | `GET /models`        | `POST /chat/completions`                  |
| Anthropic     | `anthropic`         | `GET /v1/models`     | `POST /v1/messages`                       |
| Google Gemini | `gemini`            | `GET /v1beta/models` | `POST .../models/{model}:generateContent` |
| DeepSeek      | `deepseek`          | `GET /models`        | `POST /chat/completions`                  |
| OpenRouter    | `openrouter`        | `GET /models`        | `POST /chat/completions`                  |


## 环境要求

- Python 3.11+

## 安装

建议使用虚拟环境，且**必须用 Python 3.11+ 创建**。

### Linux / macOS

```bash
cd api-monitor

# 若已有旧 .venv，先删除
rm -rf .venv

# 创建虚拟环境（确保 python3 为 3.11+）
python3 -m venv .venv
# 若系统 python3 版本过低，可指定路径，例如：
# /path/to/python3.11 -m venv .venv

# 激活虚拟环境
source .venv/bin/activate

# 升级 pip 并安装
pip install --upgrade pip
pip install -e .
```

### Windows（CMD）

```cmd
cd api-monitor

rmdir /s /q .venv

py -3.11 -m venv .venv
.venv\Scripts\activate.bat

python -m pip install --upgrade pip
pip install -e .
```

### Windows（PowerShell）

```powershell
cd api-monitor

Remove-Item -Recurse -Force .venv -ErrorAction SilentlyContinue

py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -e .
```

> PowerShell 若提示无法运行脚本，先执行：`Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

### 每次使用前：激活虚拟环境

| 系统 | 命令 |
|------|------|
| Linux / macOS | `source .venv/bin/activate` |
| Windows CMD | `.venv\Scripts\activate.bat` |
| Windows PowerShell | `.venv\Scripts\Activate.ps1` |

## 快速开始

激活虚拟环境后：

### Linux / macOS

```bash
cp config.example.yaml config.yaml
# 编辑 config.yaml，填入真实 API Key

api-monitor --config config.yaml
```

### Windows（CMD / PowerShell）

```cmd
copy config.example.yaml config.yaml
REM 编辑 config.yaml，填入真实 API Key

api-monitor --config config.yaml
```

PowerShell 复制配置可用：`Copy-Item config.example.yaml config.yaml`

## 命令行参数


| 参数              | 简写   | 说明                  | 默认值           |
| --------------- | ---- | ------------------- | ------------- |
| `--config`      | `-c` | 配置文件路径              | `config.yaml` |
| `--provider`    | `-p` | 仅检测指定平台             | 全部            |
| `--json`        |      | 以 JSON 格式输出到 stdout | 关闭            |
| `--timeout`     | `-t` | 单次请求超时（秒）           | 配置文件中的值       |
| `--concurrency` | `-n` | 并发检测数               | 配置文件中的值       |


### 示例

```bash
# 仅检测 OpenAI，5 并发，10 秒超时
api-monitor -c config.yaml -p openai -n 5 -t 10

# JSON 输出，便于脚本集成
api-monitor -c config.yaml --json

# 列出支持的平台名称
api-monitor providers
```

## 配置文件

参考 `config.example.yaml`：

```yaml
timeout: 10
concurrency: 5
max_auto_models: 20   # 未指定 models 时，自动探测的上限

providers:
  openai:
    base_url: https://api.openai.com/v1   # 可选，有默认值
    keys:
      - alias: prod
        api_key: sk-xxx
        models:                            # 指定要探测的模型
          - gpt-4o-mini
          - gpt-4o
      - alias: backup
        api_key: sk-yyy
        # 省略 models：从 /models 自动取前 max_auto_models 个

  anthropic:
    keys:
      - alias: main
        api_key: sk-ant-xxx
        models:
          - claude-3-5-haiku-20241022

  # OpenAI 兼容中转站
  openai-compatible:
    base_url: https://your-proxy.example.com/v1
    keys:
      - alias: relay
        api_key: sk-xxx
        models:
          - gpt-4o-mini
```

## 输出说明

终端表格包含以下字段：


| 字段           | 说明                                    |
| ------------ | ------------------------------------- |
| Platform     | 平台名称                                  |
| Alias        | Key 别名                                |
| Model        | 被探测的模型名；Key 级失败（如 /models 不可用）时显示 `-` |
| Key (masked) | 脱敏后的 Key，如 `sk-abc...xyz`             |
| Status       | `OK` 或 `FAILED`                       |
| HTTP         | HTTP 状态码                              |
| Latency      | 请求耗时                                  |
| Error        | 失败原因                                  |


JSON 输出示例：

```json
[
  {
    "platform": "openai",
    "alias": "prod",
    "masked_key": "sk-abc...xyz",
    "model": "gpt-4o-mini",
    "status": "OK",
    "http_status": 200,
    "latency_ms": 342.5,
    "error": null
  }
]
```

## 退出码


| 码   | 含义                        |
| --- | ------------------------- |
| `0` | 全部 Key 检测成功               |
| `1` | 存在检测失败的 Key               |
| `2` | 配置错误（文件不存在、YAML 无效、未知平台等） |


## 项目结构

```
api-monitor/
├── pyproject.toml
├── config.example.yaml
├── README.md
└── src/api_monitor/
    ├── cli.py           # CLI 入口
    ├── config.py        # YAML 配置加载
    ├── models.py        # Pydantic 数据模型
    ├── masking.py       # Key 脱敏
    ├── runner.py        # 并发调度
    └── providers/       # 各平台检测实现
```

