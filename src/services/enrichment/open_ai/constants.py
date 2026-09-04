# Extraction: the same requirements must produce the same filters.
LLM_TEMPERATURE = 0.0

# Temperature alone still lets the sampler pick other terms.
LLM_SEED = 0

# How many texts go into one embedding request while indexing.
EMBEDDING_BATCH_SIZE = 64

# The seed narrows the drift but does not end it, so criteria are reused.
FILTERS_CACHE_PREFIX = "enrichment:filters"
FILTERS_CACHE_TIMEOUT = 60 * 60 * 24
