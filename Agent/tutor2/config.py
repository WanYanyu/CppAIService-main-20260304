import os
from dataclasses import dataclass
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AGENT_DIR = os.path.dirname(BASE_DIR)

# 先加载 Agent/.env，再让 tutor2/.env 覆盖同名配置
load_dotenv(os.path.join(AGENT_DIR, ".env"))
load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)


@dataclass
class Tutor2Settings:
    model_name: str = os.getenv("TUTOR2_MODEL", "deepseek-chat")
    llm_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    llm_base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

    sandbox_api_url: str = "http://127.0.0.1:9002/api/sandbox/evaluate"

    mysql_host: str = os.getenv("MYSQL_HOST", "127.0.0.1")
    mysql_port: int = int(os.getenv("MYSQL_PORT", "3306"))
    mysql_user: str = os.getenv("MYSQL_USER", "root")
    mysql_password: str = os.getenv("MYSQL_PASSWORD", "")
    mysql_database: str = os.getenv("MYSQL_DATABASE", "openclaw")

    rag_docs_dir: str = os.getenv("TUTOR2_RAG_DOCS_DIR", os.path.join(os.path.dirname(__file__), "rag_docs"))
    rag_cache_csv: str = os.getenv("TUTOR2_TESTCASE_CACHE_CSV", os.path.join(os.path.dirname(__file__), "data", "test_cases_cache.csv"))
    rag_index_dir: str = os.getenv("TUTOR2_RAG_INDEX_DIR", os.path.join(os.path.dirname(__file__), "data", "rag_index"))

    embedding_api_key: str = os.getenv("EMBEDDING_API_KEY", "")
    embedding_base_url: str = os.getenv("EMBEDDING_BASE_URL", "")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

    langsmith_tracing: str = os.getenv("LANGSMITH_TRACING", "false")
    langsmith_api_key: str = os.getenv("LANGSMITH_API_KEY", "")
    langsmith_project: str = os.getenv("LANGSMITH_PROJECT", "cppai-tutor2")
    langsmith_endpoint: str = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")


settings = Tutor2Settings()


def _configure_langsmith_env() -> None:
    os.environ["LANGSMITH_TRACING"] = settings.langsmith_tracing
    os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
    os.environ["LANGCHAIN_ENDPOINT"] = settings.langsmith_endpoint
    if settings.langsmith_api_key:
        os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key


_configure_langsmith_env()
