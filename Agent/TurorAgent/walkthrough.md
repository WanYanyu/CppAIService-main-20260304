# 苏格拉底式代码辅导 Agent - 交付文档

## ✅ 完成功能列表

后端 Core Agent 已根据“双节点(Two-Node)”设计开发完毕，并已支持云端与本地的跨域请求。共实现了：

1. **环境与运行层** (`requirements.txt`, `.env`)
   * 通过 `python-dotenv` 实现了基于本地与服务器环境变量的安全 API 密钥管理。
2. **Schema 与接口层** (`models.py`, `main.py`)
   * 标准化了具有短期记忆 (Chat History) 的前端交互 JSON Request Schema。
   * 通过 FastAPI 提供了带有跨域支持的 `/api/tutor/chat` POST 接口。
3. **Prompt 及 AI Agent 层** (`prompts.py`, `tutor_agent.py`)
   * 实现了 **专家诊断节点**：准确找出代码在时空复杂度、逻辑漏洞上的报错原因。
   * 实现了 **苏格拉底教学节点**：严格拦截且无视用户“直接求答案”的指令，仅输出反问或单步提示。并采用异步非阻塞调用 DeepSeek 接口保证性能。
4. **测试脚本** (`mock_test.py`)
   * 随附了一个完整的构造用例（带历史对话、用户逼问场景），可直接本地调用。

---

## 🚀 运行与验证指南

### 第一步：安装依赖并在 `.env` 配置您的 Key
请确保已进入 `TurorAgent` 目录：
```bash
pip install -r requirements.txt
```
复制一份 `.env.example` 重命名为 `.env`，填入您的 DeepSeek API Key：
```env
DEEPSEEK_API_KEY="sk-xxxxxxxxxx"
# DEEPSEEK_BASE_URL="https://api.deepseek.com/v1"
# CORS_ORIGINS="*"
```

### 第二步：运行本地测试（推荐先尝试）
不依赖前端，直接在终端里观察 Agent 的拦截效果。
```bash
python mock_test.py
```
*您会发现 Agent 即便面对用户哀求，也会礼貌地拒绝直接给代码，并反问题目对于额外空间的限制。*

### 第三步：启动 FastAPI 后端服务
运行主程序，启动供前端直接调用的 API 服务：
```bash
python main.py
# 或使用: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
服务将在 `http://localhost:8000` 拉起。

---

## 🔌 前端接入示例 (Dashboard & Editor 界面对接)

在已有网页上的“聊天框”组件中，当用户点击发送时，使用以下 Fetch 请求调用该接口：

```javascript
// 前端 fetch 示例代码
async function askTutor() {
    const requestBody = {
        "problem_id": "1",
        "problem_description": "两数之和...", // 从您的题目库读取
        "current_code": editor.getValue(),   // 从右侧编辑器读取
        "test_case_results": "Runtime Error on Line 3...", // 可选填
        "chat_history": [                    // 从当前聊天框记录中读取
            {"role": "user", "content": "怎么写？"},
            {"role": "assistant", "content": "我们看看题目要求..."}
        ],
        "user_message": "依然报错，越界了"  // 当前用户发的消息
    };

    const response = await fetch("http://localhost:8000/api/tutor/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody)
    });

    const data = await response.json();
    console.log("教学Agent的回复: ", data.reply);
    
    // 把 data.reply 渲染回网页聊天面板中
}
```

> [!TIP]
> 部署到云服务器时，只需把代码完整拉取到服务器，安装环境后，建议使用 `uvicorn main:app --host 0.0.0.0 --port 80 --workers 4` 等形式在后台长期运行，并在服务器面板开放对外映射的主机端口即可。前端对应修改 Fetch URL。
