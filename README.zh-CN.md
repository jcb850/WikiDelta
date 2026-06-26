# WikiDelta

中文说明 | [English README](./README.md)

WikiDelta 是一个面向 llmwiki 的 `.wd` 知识源生命周期工具。它把文件系统里的知识源封装成可维护的 `.wd` 文件：保存当前生效内容和来源配置，并且只在存在待审阅候选内容时保存来源快照。

第一版遵循一个清晰约束：

```text
1 个 .wd 文件 = 1 个知识单元 = 1 个 source = 1 个 effective 内容区
```

## 适用场景

- 知识源维护在文件系统中，但文件类型很多，例如 Markdown、文本、HTML、JSON、PDF、网页。
- 希望有一个明确的“当前生效内容”概念，避免来源刷新后直接污染知识库。
- llmwiki 项目的 raw source 目录需要一种更适合持续维护和 Agent 操作的源文件格式。
- Agent 需要通过稳定 CLI 和 JSON 输出维护知识源生命周期。

## `.wd` 文件结构

`.wd` 本质上是一个 Markdown 文件，由 YAML front matter 和命名内容区组成：

```markdown
---
wd_version: 1
id: pricing-policy
title: 计费规则
status: active
content_type: markdown
tags:
  - pricing
  - policy
source:
  fetcher: builtin.file
  fetch:
    path: ./pricing.md
  transformer: builtin.markdown
  transform: {}
sync:
  strategy: review_before_apply
---

<!-- wd:effective -->
# 计费规则

这里是当前生效内容，会被导入 llmwiki。
<!-- /wd:effective -->

<!-- wd:notes -->
维护备注、审阅判断、为什么接受或拒绝某些来源变化。
<!-- /wd:notes -->
```

当 `wd update` 发现来源内容和 `wd:effective` 不一致时，WikiDelta 才会临时写入候选区：

```markdown
<!-- wd:source_snapshot -->
# 计费规则

这里是最近一次从来源获取并转换后的候选内容。
<!-- /wd:source_snapshot -->
```

核心规则：

- `wd:effective` 是默认唯一入库内容。
- `wd:source_snapshot` 是可选候选内容，只在需要审阅时出现，用于审阅和 diff，不会直接入库。
- `wd:notes` 是维护备注，不会默认进入 llmwiki。
- `id` 是知识单元稳定身份，用于状态、缓存、review 和后续 upsert。
- 初次 `wd add` 只写入 `effective`；后续 `wd update` 只有在来源内容变化时才创建 `source_snapshot`。

## 安装与运行

当前项目是 Python CLI 包。开发环境中可以直接使用 `PYTHONPATH` 运行：

```bash
PYTHONPATH=src python3 -m wikidelta.cli --help
```

安装为本地可执行命令：

```bash
pip install -e .
wd --help
```

## 快速开始

初始化工作区：

```bash
wd init --mode llmwiki_project
```

把本地 Markdown 文件封装成 `.wd`：

```bash
wd add ./policy.md --into raw_sources/policy
```

来源文件变化后刷新候选快照：

```bash
wd update raw_sources/policy/policy.wd
```

查看状态：

```bash
wd status --json
```

生成审阅材料：

```bash
wd review raw_sources/policy/policy.wd --json
```

确认接受候选内容为生效内容：

```bash
wd apply raw_sources/policy/policy.wd --strategy replace --yes
```

作为 llmwiki 兼容桥，只提取 `wd:effective`：

```bash
wd ingest raw_sources/policy/policy.wd --json
```

## CLI 命令

```text
wd init      初始化 .wikidelta 状态目录
wd add       从本地文件或 URL 创建 .wd
wd update    刷新来源，并只在需要审阅时创建 source_snapshot
wd status    扫描 .wd 状态
wd review    生成 review JSON 和 patch
wd apply     把候选内容应用到 effective
wd ingest    提取 effective，作为 llmwiki 兼容桥
```

`wd status` 在命令成功但存在待审阅内容时返回退出码 `3`。这不是执行失败，而是告诉 Agent 或脚本“有 pending review 需要处理”。

## 内置来源与转换

`wd add` 会根据输入自动推断常见来源管线：

```text
*.md        builtin.file + builtin.markdown
*.txt       builtin.file + builtin.text
*.html      builtin.file + builtin.html_to_markdown
*.json      builtin.file + builtin.json_to_markdown
*.pdf       builtin.file + builtin.pdf_to_markdown
http(s)://  builtin.http + builtin.html_to_markdown
```

也可以在 `.wd` 中手动维护 source 配置：

```yaml
source:
  fetcher: builtin.http
  fetch:
    url: https://example.com/policy
  transformer: builtin.html_to_markdown
  transform:
    selector: main
```

## llmwiki 项目模式

推荐把 `.wd` 直接放在 llmwiki 项目的 raw source 文件结构里：

```text
llmwiki-project/
  raw_sources/
    pricing/pricing-policy.wd
    policy/refund-policy.wd
```

这种模式下，`.wd` 所属项目由目录上下文决定，不需要为每个 `.wd` 配置 llmwiki 的 `base_url` 或 `project`。

入库原则是：llmwiki 或兼容桥只能读取 `wd:effective`，不能把整个 `.wd` 当普通 Markdown 导入，否则 source 配置、候选快照和 notes 会污染知识库。

## Agent 友好约定

主命令支持 JSON 输出和显式 workspace：

```bash
wd status --workspace /path/to/repo --json
```

影响 `effective` 的生命周期操作需要显式确认：

```bash
wd apply path/to/file.wd --strategy replace --yes
```

推荐 Agent 工作流：

```text
1. wd status --json
2. 对 pending_review 的文件执行 wd review --json
3. 读取 .wikidelta/reviews/<id>.json 和 .patch
4. 判断是否接受变化
5. wd apply <file.wd> --strategy replace --yes
6. wd ingest <file.wd> --json
```

## 脚本扩展

复杂来源可以使用 `script.python`。脚本从 stdin 读取 JSON，并向 stdout 输出 JSON。

`.wd` 示例：

```yaml
source:
  fetcher: script.python
  fetch:
    entry: ./fetchers/feishu_doc.py
    args:
      doc_id: abc123
  transformer: builtin.markdown
  transform: {}
```

成功输出：

```json
{
  "ok": true,
  "contentType": "text/plain",
  "content": "Fetched content",
  "metadata": {}
}
```

失败输出：

```json
{
  "ok": false,
  "error": {
    "code": "AUTH_FAILED",
    "message": "Missing token",
    "retryable": false
  }
}
```

凭证建议通过环境变量传入脚本，不要写入 `.wd` 文件。

## 测试

运行完整测试：

```bash
pytest -v
```

当前测试覆盖 `.wd` 解析、仓库初始化、source 推断、`wd add/update/status/review/apply/ingest`、脚本协议和端到端生命周期。
