FULL_RESUMES_INDEX = "full_resumes"

TIMEOUT = 30
MAX_RETRIES = 3

# Chunks are carried by inner hits; in the body they are dead weight.
SOURCE_EXCLUDES = [
    "experience.description_chunks",
    "experience.head_vector",
]

# CEFR levels in ascending order; "l1" marks a native speaker.
LANGUAGE_LEVELS = ("a1", "a2", "b1", "b2", "c1", "c2", "l1")

MONTHS_PER_YEAR = 12

# Neighbours each vector clause retrieves, counted in chunks, not resumes.
KNN_CANDIDATES = 2000

# The recruiter names a technology; the model only guesses one.
MUST_KEYWORDS_BOOST = 1.0
REQUIRED_KEYWORDS_BOOST = 0.4

# What a candidate did on the job outweighs what they listed as a skill.
DESCRIPTION_KEYWORDS_BOOST = 2.0

# A shorter stint in the wanted role reads as a job someone lost.
MIN_ROLE_MONTHS = 12
SHORT_ROLE_WEIGHT = 0.2

# Years in the role are counted at this rate before the slider scales them.
ROLE_TENURE_FACTOR = 0.1

# Splits one required term into the spellings that all mean the same.
SPELLING_SEPARATOR = "|"

# Everything searchable is copied into full_text when a resume is indexed.
# Self-listed skills are not boosted: only one of the sources exports them.
KEYWORD_FIELDS = ["full_text", "title^1.5"]

# Weight of "position — company" against the description of the same job.
HEAD_VECTOR_BOOST = 1.0

# "avg" asks whether the whole career fits; "max" rewards one lucky job.
EXPERIENCE_SCORE_MODE = "avg"

# How many resumes each criterion returns. The pool is fixed at this depth
# and normalised once: a candidate outside it can never be slid into view.
POOL_DEPTH = 1000

# The little of a resume the pool list in the browser gets to show.
BRIEF_FIELDS = [
    "title",
    "alternate_url",
    "area.name",
    "age",
    "salary.amount",
    "salary.currency",
    "total_experience.months",
]

# How many matching jobs and chunks are returned as an explanation.
INNER_HITS_SIZE = 3
