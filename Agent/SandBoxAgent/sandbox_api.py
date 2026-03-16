import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Ensure environment vars are loaded at module start
load_dotenv()

from models import EvaluationRequest, EvaluationResult
from sandbox_agent import evaluate_code

app = FastAPI(title="Sandbox Execution Agent API", description="带真实物理执行环境的代码评测系统")

cors_origins_str = os.getenv("CORS_ORIGINS", "*")
cors_origins = [origin.strip() for origin in cors_origins_str.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/sandbox/evaluate", response_model=EvaluationResult)
async def sandbox_evaluate(request: EvaluationRequest):
    """
    1. Executing Python code safely in subprocess
    2. Analyzing actual Stdout & Tracebacks
    3. Returning Natural Language explanations
    """
    try:
        response = await evaluate_code(request)
        return response
    except Exception as e:
        print(f"Error executing sandbox request: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "Sandbox Evaluation Agent is online."}

if __name__ == "__main__":
    import uvicorn
    # 建议使用全新的端口，防止与辅导 Agent 冲突
    uvicorn.run("sandbox_api:app", host="0.0.0.0", port=8002, reload=True)
