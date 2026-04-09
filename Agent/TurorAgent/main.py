from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import sys

# 加载环境变量 (需要放在最前面，让其它模块 import 时能直接可用)
load_dotenv()

from models import TutorChatRequest, TutorChatResponse

# 兼容层：优先使用新的 tutor2 多 Agent 实现，失败时降级到旧实现
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
AGENT_DIR = os.path.dirname(CURRENT_DIR)
if AGENT_DIR not in sys.path:
    sys.path.append(AGENT_DIR)

try:
    from tutor2 import process_tutor_request_v2  # type: ignore
except Exception:
    process_tutor_request_v2 = None

from tutor_agent import process_tutor_request

app = FastAPI(title="Socratic Tutor Agent API", description="启发式代码辅导后端系统")

# 处理 CORS 跨域请求
cors_origins_str = os.getenv("CORS_ORIGINS", "*")
cors_origins = [origin.strip() for origin in cors_origins_str.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/tutor/chat", response_model=TutorChatResponse)
async def tutor_chat(request: TutorChatRequest):
    try:
        if process_tutor_request_v2 is not None:
            response = await process_tutor_request_v2(request)
            return TutorChatResponse(**response)

        response = await process_tutor_request(request)
        return response
    except Exception as e:
        # 处理异常情况，返回 500 并在控制台打印
        print(f"Error processing tutor request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tutor/v2/chat", response_model=TutorChatResponse)
async def tutor_chat_v2(request: TutorChatRequest):
    try:
        if process_tutor_request_v2 is None:
            raise RuntimeError("tutor2 is unavailable, please check dependencies")
        response = await process_tutor_request_v2(request)
        return TutorChatResponse(**response)
    except Exception as e:
        print(f"Error processing tutor v2 request: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "Socratic Tutor Agent is running."}

if __name__ == "__main__":
    import uvicorn
    # 本地直接运行此脚本时的启动方式 (生产环境建议用 CLI 或者 gunicorn)
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=False)
