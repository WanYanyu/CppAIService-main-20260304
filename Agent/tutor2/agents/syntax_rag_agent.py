import json
import math
import os
from typing import Dict, List, Tuple

from openai import AsyncOpenAI

from ..config import settings


def _list_pdf_files() -> List[str]:
    if not os.path.isdir(settings.rag_docs_dir):
        return []
    return sorted(
        [
            os.path.join(settings.rag_docs_dir, f)
            for f in os.listdir(settings.rag_docs_dir)
            if f.lower().endswith(".pdf")
        ]
    )


def _pdf_signature(pdf_files: List[str]) -> List[Dict[str, str]]:
    sig = []
    for fp in pdf_files:
        st = os.stat(fp)
        sig.append({"path": fp, "mtime": str(st.st_mtime_ns), "size": str(st.st_size)})
    return sig


def _read_pdf_texts(pdf_files: List[str]) -> List[Tuple[str, str]]:
    from pypdf import PdfReader

    docs = []
    for fp in pdf_files:
        reader = PdfReader(fp)
        pages = []
        for p in reader.pages:
            pages.append(p.extract_text() or "")
        docs.append((fp, "\n".join(pages)))
    return docs


def _chunk_text(text: str, chunk_size: int = 900, overlap: int = 150) -> List[str]:
    text = (text or "").strip()
    if not text:
        return []

    chunks: List[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_size, n)
        chunks.append(text[start:end])
        if end >= n:
            break
        start = max(0, end - overlap)
    return chunks


def _cosine(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return -1.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return -1.0
    return dot / (na * nb)


def _index_paths() -> Tuple[str, str]:
    os.makedirs(settings.rag_index_dir, exist_ok=True)
    meta_path = os.path.join(settings.rag_index_dir, "meta.json")
    data_path = os.path.join(settings.rag_index_dir, "vectors.json")
    return meta_path, data_path


async def _embed_texts(client: AsyncOpenAI, texts: List[str]) -> List[List[float]]:
    vectors: List[List[float]] = []
    batch_size = 24
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        resp = await client.embeddings.create(model=settings.embedding_model, input=batch)
        for item in resp.data:
            vectors.append(item.embedding)
    return vectors


async def _load_or_build_index() -> Tuple[List[Dict], List[List[float]], str]:
    pdf_files = _list_pdf_files()
    if not pdf_files:
        return [], [], "RAG 资料库为空：请把 C++/Python PDF 放到 Agent/tutor2/rag_docs。"

    emb_key = settings.embedding_api_key or settings.llm_api_key
    emb_base_url = settings.embedding_base_url or settings.llm_base_url
    if not emb_key or not emb_base_url or not settings.embedding_model:
        return [], [], "未配置 embedding 参数，请检查 EMBEDDING_API_KEY / EMBEDDING_BASE_URL / EMBEDDING_MODEL。"

    meta_path, data_path = _index_paths()
    current_meta = {
        "embedding_model": settings.embedding_model,
        "embedding_base_url": emb_base_url,
        "pdf_signature": _pdf_signature(pdf_files),
    }

    if os.path.exists(meta_path) and os.path.exists(data_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                cached_meta = json.load(f)
            if cached_meta == current_meta:
                with open(data_path, "r", encoding="utf-8") as f:
                    payload = json.load(f)
                return payload.get("chunks", []), payload.get("vectors", []), ""
        except Exception:
            pass

    docs = _read_pdf_texts(pdf_files)
    chunks: List[Dict] = []
    for fp, txt in docs:
        for idx, ck in enumerate(_chunk_text(txt)):
            chunks.append({"doc": os.path.basename(fp), "chunk_id": idx, "text": ck})

    if not chunks:
        return [], [], "PDF 已读取，但未解析出可用文本。"

    client = AsyncOpenAI(api_key=emb_key, base_url=emb_base_url)
    try:
        vectors = await _embed_texts(client, [x["text"] for x in chunks])
    except Exception as e:
        return [], [], (
            "Embedding 索引构建失败，请检查 EMBEDDING_BASE_URL 与 EMBEDDING_MODEL 是否匹配。"
            f" 原始错误: {e}"
        )

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(current_meta, f, ensure_ascii=False, indent=2)
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump({"chunks": chunks, "vectors": vectors}, f, ensure_ascii=False)

    return chunks, vectors, ""


async def run_syntax_rag_agent(user_message: str, code: str) -> str:
    chunks, vectors, err = await _load_or_build_index()
    if err:
        return err

    query = (user_message or "") + "\n\n" + (code or "")
    query = query.strip()
    if not query:
        query = "请给出与当前题目相关的 C++ / Python 语法知识点"

    emb_key = settings.embedding_api_key or settings.llm_api_key
    emb_base_url = settings.embedding_base_url or settings.llm_base_url
    client = AsyncOpenAI(api_key=emb_key, base_url=emb_base_url)
    try:
        q_resp = await client.embeddings.create(model=settings.embedding_model, input=query)
    except Exception as e:
        return (
            "Embedding 查询失败，请检查 EMBEDDING_API_KEY / EMBEDDING_BASE_URL / EMBEDDING_MODEL。"
            f" 原始错误: {e}"
        )
    q_vec = q_resp.data[0].embedding

    scored = []
    for i, vec in enumerate(vectors):
        score = _cosine(q_vec, vec)
        scored.append((score, i))
    scored.sort(key=lambda x: x[0], reverse=True)

    top = scored[:3]
    if not top or top[0][0] <= 0:
        return "RAG 未检索到高相关语法片段。"

    sections = []
    for rank, (score, idx) in enumerate(top, start=1):
        chunk = chunks[idx]
        sections.append(
            f"[{rank}] 来源: {chunk['doc']} | 相似度: {score:.3f}\n{chunk['text'][:520]}"
        )

    return "语法 RAG 检索结果：\n\n" + "\n\n".join(sections)
