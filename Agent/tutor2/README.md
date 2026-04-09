# tutor2 (LangGraph Multi-Agent)

这是新的 Tutor 架构目录，目标：
- 保持现有接口契约兼容
- 使用 LangGraph 实现 Supervisor + 多子 Agent

## 子 Agent
1. runtime_agent：调用 Sandbox 服务执行真实代码
2. testcase_agent：先查 MySQL 的 `test_cases`，缺失时生成并回填 MySQL + CSV
3. complexity_agent：代码通过后分析时空复杂度
4. syntax_rag_agent：向量化 RAG（PDF 切块 + embedding + 本地向量索引）

## 样例获取 Agent（你要的输入输出契约）
- 输入：`problem_id(str)` + `problem_description(str)`
- 输出：`test_cases_text(str)`，格式如下：

```text
#case 1
input:
1 2 3
expected_output:
6
---
```

- 在流程中会做两步：
	1) `run_testcase_agent_text(...)` 生成 `str`；
	2) `parse_test_cases_text(...)` 解析为沙盒需要的 `[{input, expected_output}]`，再调用 runtime/sandbox。

## RAG 文档放置
把 PDF 放到：`Agent/tutor2/rag_docs/`
例如：
- `cpp_primer.pdf`
- `python_reference.pdf`

本地索引默认会写到：`Agent/tutor2/data/rag_index/`

## 环境变量（示例）
- `TUTOR2_MODEL`
- `DEEPSEEK_API_KEY`
- `DEEPSEEK_BASE_URL`
- `SANDBOX_API_URL`
- `MYSQL_HOST`
- `MYSQL_PORT`
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `MYSQL_DATABASE`
- `EMBEDDING_API_KEY`
- `EMBEDDING_BASE_URL`
- `EMBEDDING_MODEL`

## Embedding Key 填写位置
你在部署时把 key 填到：
- `Agent/tutor2/.env`（可由 `.env.example` 复制得到）

最小可用配置：
```env
EMBEDDING_API_KEY=你的embedding服务key
EMBEDDING_BASE_URL=你的embedding服务base_url
EMBEDDING_MODEL=你的embedding模型名
```

## LangSmith 可视化观测（新增）
在 `Agent/tutor2/.env` 增加：

```env
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=你的langsmith_key
LANGSMITH_PROJECT=cppai-tutor2
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
```

开启后可看到：
- 每次 `/api/tutor/v2/chat` 的调用链路
- supervisor/testcase/runtime/complexity/syntax_rag/composer 的节点执行状态
- 部分 LLM 节点的 token 使用量（目前已接入 supervisor、testcase 生成、complexity）
