import asyncio
import csv
import json
import os
import re
from typing import List, Dict, Any, Tuple
from openai import AsyncOpenAI
from ..config import settings


def _read_mysql_test_cases(problem_id: str) -> str:
    try:
        import pymysql  # optional dependency
    except Exception:
        return ""

    try:
        conn = pymysql.connect(
            host=settings.mysql_host,
            port=settings.mysql_port,
            user=settings.mysql_user,
            password=settings.mysql_password,
            database=settings.mysql_database,
            charset="utf8mb4",
            connect_timeout=3,
            read_timeout=5,
            write_timeout=5,
            autocommit=True,
        )
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT test_cases FROM study_records WHERE problem_id=%s ORDER BY id DESC LIMIT 1",
                (int(problem_id),),
            )
            row = cursor.fetchone()
            return row[0] if row and row[0] else ""
    except Exception:
        return ""
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _normalize_test_cases(raw: str) -> List[Dict[str, str]]:
    if not raw:
        return []
    try:
        val = json.loads(raw)
        if isinstance(val, list):
            out = []
            for item in val:
                if isinstance(item, dict):
                    out.append(
                        {
                            "input": str(item.get("input", "")),
                            "expected_output": str(item.get("expected_output", "")),
                        }
                    )
            return out
        return []
    except Exception:
        return []


async def _synthesize_test_cases(problem_id: str, description: str) -> List[Dict[str, str]]:
    cases, _ = await _synthesize_test_cases_with_meta(problem_id, description)
    return cases


async def _synthesize_test_cases_with_meta(problem_id: str, description: str) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
    meta: Dict[str, Any] = {"source": "fallback", "token_usage": {}}
    samples = [
        {
            "input": "\n",
            "expected_output": "",
        }
    ]

    if "two sum" in description.lower() or "两数之和" in description:
        samples = [
            {"input": "4\n2 7 11 15\n9\n", "expected_output": "0 1"},
            {"input": "3\n3 2 4\n6\n", "expected_output": "1 2"},
        ]
        meta["source"] = "heuristic_hardcoded"

    if (
        "有效括号" in description
        or "valid parentheses" in description.lower()
        or problem_id == "20"
    ):
        samples = [
            {"input": "()[]{}\n", "expected_output": "true"},
            {"input": "(]\n", "expected_output": "false"},
            {"input": "([)]\n", "expected_output": "false"},
            {"input": "{[]}\n", "expected_output": "true"},
        ]
        meta["source"] = "heuristic_hardcoded"

    if (
        "回文数" in description
        or "palindrome number" in description.lower()
        or problem_id == "121"
    ):
        samples = [
            {"input": "121\n", "expected_output": "true"},
            {"input": "-121\n", "expected_output": "false"},
            {"input": "10\n", "expected_output": "false"},
            {"input": "0\n", "expected_output": "true"},
        ]
        meta["source"] = "heuristic_hardcoded"

    if not _has_valid_expected_output(samples):
        searched, searched_meta = await _synthesize_test_cases_via_search(problem_id, description)
        if _has_valid_expected_output(searched):
            samples = searched
            meta.update(searched_meta)

    return samples, meta


def _has_valid_expected_output(test_cases: List[Dict[str, str]]) -> bool:
    return bool(test_cases) and any((x.get("expected_output", "") or "").strip() for x in test_cases)


def _normalize_generated_cases(cases: List[Dict[str, str]], limit: int = 6) -> List[Dict[str, str]]:
    normalized: List[Dict[str, str]] = []
    for case in cases[:limit]:
        if not isinstance(case, dict):
            continue
        case_input = str(case.get("input", ""))
        expected_output = str(case.get("expected_output", ""))
        if not case_input.strip() or not expected_output.strip():
            continue
        if not case_input.endswith("\n"):
            case_input += "\n"
        normalized.append({"input": case_input, "expected_output": expected_output.strip()})
    return normalized


def _search_problem_examples(problem_id: str, description: str) -> str:
    try:
        module = __import__("langchain_community.tools", fromlist=["DuckDuckGoSearchResults"])
        DuckDuckGoSearchResults = getattr(module, "DuckDuckGoSearchResults")
    except Exception:
        return ""

    query = f"LeetCode {problem_id} {description[:120]} examples input output"
    try:
        search = DuckDuckGoSearchResults(max_results=5)
        result = search.invoke(query)
        return str(result)
    except Exception:
        return ""


async def _extract_cases_with_llm(problem_id: str, description: str, search_text: str) -> Tuple[List[Dict[str, str]], Dict[str, int]]:
    if not settings.llm_api_key:
        return [], {}

    prompt = (
        "你是编程题测试样例提取器。"
        "根据题目描述和搜索结果，提取3-6条高质量测试样例。"
        "仅返回 JSON 数组，不要 markdown，不要解释。"
        "格式: [{\"input\":\"...\",\"expected_output\":\"...\"}]。"
        "要求：input 和 expected_output 都必须非空；input 保持可直接喂给 stdin。"
        f"\nproblem_id={problem_id}"
        f"\n题目描述:\n{description[:1200]}"
        f"\n搜索结果:\n{search_text[:4000]}"
    )

    try:
        client = AsyncOpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)
        resp = await asyncio.wait_for(
            client.chat.completions.create(
                model=settings.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            ),
            timeout=12,
        )
        usage = getattr(resp, "usage", None)
        token_usage = {
            "prompt_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
            "completion_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
            "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
        }
        content = (resp.choices[0].message.content or "").strip()
        parsed = _parse_cases_json_from_text(content)
        if isinstance(parsed, list):
            return _normalize_generated_cases(parsed), token_usage
        return [], token_usage
    except Exception:
        return [], {}


def _parse_cases_json_from_text(content: str):
    if not content:
        return []

    try:
        return json.loads(content)
    except Exception:
        pass

    fenced = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", content, flags=re.DOTALL)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except Exception:
            pass

    arr = re.search(r"(\[\s*\{.*\}\s*\])", content, flags=re.DOTALL)
    if arr:
        try:
            return json.loads(arr.group(1))
        except Exception:
            pass

    return []


async def _synthesize_test_cases_via_search(problem_id: str, description: str) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
    search_text = _search_problem_examples(problem_id, description)
    cases, token_usage = await _extract_cases_with_llm(problem_id, description, search_text)
    source = "duckduckgo_plus_llm" if search_text.strip() else "llm_only"
    return cases, {"source": source, "token_usage": token_usage}


def _append_csv_cache(problem_id: str, description: str, test_cases: List[Dict[str, str]]) -> None:
    os.makedirs(os.path.dirname(settings.rag_cache_csv), exist_ok=True)
    file_exists = os.path.exists(settings.rag_cache_csv)
    with open(settings.rag_cache_csv, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["problem_id", "problem_description", "test_cases_json"])
        writer.writerow([problem_id, description[:500], json.dumps(test_cases, ensure_ascii=False)])


def _write_mysql_test_cases(problem_id: str, test_cases: List[Dict[str, str]]) -> None:
    try:
        import pymysql
    except Exception:
        return

    try:
        conn = pymysql.connect(
            host=settings.mysql_host,
            port=settings.mysql_port,
            user=settings.mysql_user,
            password=settings.mysql_password,
            database=settings.mysql_database,
            charset="utf8mb4",
            connect_timeout=3,
            read_timeout=5,
            write_timeout=5,
            autocommit=True,
        )
        test_cases_json = json.dumps(test_cases, ensure_ascii=False)
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE study_records SET test_cases=%s WHERE problem_id=%s",
                (test_cases_json, int(problem_id)),
            )
    except Exception:
        return
    finally:
        try:
            conn.close()
        except Exception:
            pass


async def run_testcase_agent(problem_id: str, problem_description: str) -> List[Dict[str, str]]:
    cases, _ = await run_testcase_agent_with_meta(problem_id, problem_description)
    return cases


async def run_testcase_agent_with_meta(problem_id: str, problem_description: str) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
    raw = _read_mysql_test_cases(problem_id)
    normalized = _normalize_test_cases(raw)
    if normalized and any((x.get("expected_output", "") or "").strip() for x in normalized):
        return normalized, {"source": "mysql_cache", "token_usage": {}}

    generated, meta = await _synthesize_test_cases_with_meta(problem_id, problem_description)
    _write_mysql_test_cases(problem_id, generated)
    _append_csv_cache(problem_id, problem_description, generated)
    return generated, meta


def format_test_cases_as_text(test_cases: List[Dict[str, str]]) -> str:
    lines: List[str] = []
    for idx, case in enumerate(test_cases, start=1):
        case_input = str(case.get("input", ""))
        case_output = str(case.get("expected_output", ""))
        lines.append(f"#case {idx}")
        lines.append("input:")
        lines.append(case_input)
        lines.append("expected_output:")
        lines.append(case_output)
        lines.append("---")
    return "\n".join(lines).strip()


def parse_test_cases_text(test_cases_text: str) -> List[Dict[str, str]]:
    if not test_cases_text or not test_cases_text.strip():
        return []

    chunks = [x.strip() for x in re.split(r"\n---\s*\n|\n---\s*$", test_cases_text.strip()) if x.strip()]
    parsed: List[Dict[str, str]] = []

    for chunk in chunks:
        input_match = re.search(r"input:\s*\n(.*?)(?:\nexpected_output:|$)", chunk, flags=re.DOTALL)
        output_match = re.search(r"expected_output:\s*\n(.*)$", chunk, flags=re.DOTALL)

        case_input = input_match.group(1).strip("\n") if input_match else ""
        case_output = output_match.group(1).strip("\n") if output_match else ""
        parsed.append({"input": case_input, "expected_output": case_output})

    return parsed


async def run_testcase_agent_text(problem_id: str, problem_description: str) -> str:
    test_cases, _ = await run_testcase_agent_with_meta(problem_id, problem_description)
    return format_test_cases_as_text(test_cases)
