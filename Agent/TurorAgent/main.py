from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

# 加载环境变量 (需要放在最前面，让其它模块 import 时能直接可用)
load_dotenv()

from models import TutorChatRequest, TutorChatResponse
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
        response = await process_tutor_request(request)
        return response
    except Exception as e:
        # 处理异常情况，返回 500 并在控制台打印
        print(f"Error processing tutor request: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "Socratic Tutor Agent is running."}

if __name__ == "__main__":
    import uvicorn
    # 本地直接运行此脚本时的启动方式 (生产环境建议用 CLI 或者 gunicorn)
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=False)
