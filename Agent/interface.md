# AI 辅导与动态沙盒评测系统接口文档

本项目包含了两个独立的微服务 Agent 节点：
1. **苏格拉底辅导 Agent (Tutor Agent)**：运行在 `8000` 端口，提供多轮启发式代码纠错服务。
2. **沙盒执行与评测 Agent (SandBox Agent)**：运行在 `8001` 端口，提供物理级的代码安全执行与终端报错分析服务。

以下将列出供任何外部项目环境（Vue/React 网站，小程序，或其他第三方服务）接入时所需要的核心 API。

---

## 1. 沙盒执行与动态评测 API

**服务端口**: `http://<服务器IP>:8001`  
**功能描述**: 接收一段纯代码和期望的测试用例，安全编译运行，抓取标准错误，并利用 AI 将 Traceback 转为人话进行分析诊断。

### 1.1 提交代码进行物理执行与诊断

**请求 URL**: `POST /api/sandbox/evaluate`  
**Header**: `Content-Type: application/json`

**请求体 (JSON Request):**
```json
{
  "language": "python",              // 支持 "python" 或 "cpp"
  "code": "def solve():\n  pass",    // 用户在代码编辑器中编写的源代码文本
  "test_cases": [
    {
      "input": "2,7,11,15\n9",       // 喂给标准输入的字符串 (sys.stdin / cin)
      "expected_output": "0,1"       // 期望捕获的标准输出，如用于验证逻辑正确与否
    }
  ]
}
```

**响应体 (JSON Response):**
```json
{
  "status": "Wrong Answer",          // 评测状态枚举: Passed | Compilation Error | Runtime Error | Time Limit Exceeded | Wrong Answer | Error
  "stdout_log": "...",               // 程序真实输出的标准打印日志 (可供前端展示)
  "stderr_log": "...",               // 程序执行或编译过程中的原生堆栈报错 (如 traceback)
  "ai_feedback": "你的代码在第5行发生了越界..." // 只有报错时才有：AI 对报错进行的人类友好诊断分析报告，如果没有报错，该字段通常是表扬语句或 null
}
```

---

## 2. 启发式代码辅导 API

**服务端口**: `http://<服务器IP>:8000`  
**功能描述**: 一个苏格拉底风格的导师聊天接口，不直接告知代码答案，而是基于沙盒执行结果引导用户去发现问题在哪。

### 2.1 向导师寻求建议 (带上下文聊天机制)

**请求 URL**: `POST /api/tutor/chat`  
**Header**: `Content-Type: application/json`

**请求体 (JSON Request):**
```json
{
  "problem_id": "two-sum",           // 题号或题目标识符 (必需)
  "problem_description": "两数之和：给定数组...", // 这道题的完整题目描述与要求 (必需)
  "current_code": "def ...",         // 用户当前最新的代码 (必需)
  "test_case_results": "Runtime Error...\nUser got IndexError on...", // 可选字段：将沙盒服务返回的 status 或 ai_feedback 扔在这里让导师知道发生了什么
  
  "chat_history": [                  // 多轮聊天的记忆数组，存放此前的历史对话记录。初次提问可传空数组 []
    {
      "role": "user",
      "content": "代码依然报越界错误了，能再给我点提示吗？"
    },
    {
      "role": "assistant",
      "content": "好的，请看一下你的 while 循环终止条件..."
    }
  ],
  
  "user_message": "我改了这里，帮我看看对了吗？" // 用户本次发送在输入框里新说的话，如果只是提交求助，可以直接传 "我的代码哪里有问题？"
}
```

**响应体 (JSON Response):**
```json
{
  "reply": "我注意到你虽然改了循环变量 `i`，但在做加法时仍然访问了 `nums[i+1]`，如果此时 `i` 已经是数组最后一个元素呢？你会怎么修复它？"
}
```

---

## 3. 部署与接入建议

- 这是两套纯后端的无状态微服务。每次请求结束之后不会主动保存在服务器上的数据库中，**聊天记忆 `chat_history` 需要由前端网页（如 Vue/React 组件的 state）来负责存储保管**，并在每次呼叫 API 时带上。
- **防止跨域 (CORS)**：已在两个服务的 FastAPI 配置中启用了跨域允许，可在生产环境中通过设置 `.env` 环境变量的 `CORS_ORIGINS=https://您的域名.com` 进行限制。
- 启动指令：
  ```bash
  cd TurorAgent && nohup uvicorn main:app --host 0.0.0.0 --port 8000 &
  cd SandBoxAgent && nohup uvicorn sandbox_api:app --host 0.0.0.0 --port 8001 &
  ```
