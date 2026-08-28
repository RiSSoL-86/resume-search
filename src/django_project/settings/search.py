from django_project.settings import env

# --- OpenSearch ---
OPENSEARCH_HOSTS = env.list(
    "OPENSEARCH_HOSTS",
    default=["http://localhost:9200"],
)

# --- OpenAI ---
OPENAI_API_KEY = env("OPENAI_API_KEY", default="")
OPENAI_EMBEDDING_MODEL = env(
    "OPENAI_EMBEDDING_MODEL",
    default="text-embedding-3-small",
)
OPENAI_EMBEDDING_DIMENSION = env.int(
    "OPENAI_EMBEDDING_DIMENSION",
    default=1536,
)
OPENAI_LLM_MODEL = env("OPENAI_LLM_MODEL", default="gpt-4.1")
