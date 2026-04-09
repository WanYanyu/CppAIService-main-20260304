import httpx
from typing import Dict, Any, List
from ..config import settings


async def run_code_agent(code: str, test_cases: List[Dict[str, str]]) -> Dict[str, Any]:
    payload_cases = test_cases or [{"input": "", "expected_output": ""}]
    payload = {
        "language": "cpp",
        "code": code,
        "test_cases": payload_cases,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(settings.sandbox_api_url, json=payload)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        return {
            "status": "Error",
            "stdout_log": "",
            "stderr_log": f"Runtime agent failed: {e}",
            "ai_feedback": None,
        }
