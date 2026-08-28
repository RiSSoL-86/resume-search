# How many resumes are chunked, embedded and indexed per round trip.
BATCH_SIZE = 16

CHUNK_SIZE = 512
CHUNK_OVERLAP = 64

# A chunk shorter than this is folded into its neighbour.
CHUNK_MIN_CHARS = 30

MEGABYTE = 1024 * 1024

# One upload carries the export of a team, never a whole database.
MAX_RESUME_BYTES = 2 * MEGABYTE
MAX_RESUMES = 5_000

ZIP_SIGNATURE = b"PK\x03\x04"

# An archive zipped on a mac carries a shadow copy of every file.
MACOS_DIRECTORY = "__MACOSX/"
MACOS_PREFIX = "._"

# The humart export states the amount, never the currency.
DEFAULT_CURRENCY = "RUR"

MONTHS_IN_YEAR = 12

TOO_MANY_RESUMES = "В файле {} резюме, обработаны первые {}."
LARGE_RESUME = "{}: файл больше {} МБ."
NOT_AN_OBJECT = "{}: это не JSON-объект резюме."
NOT_A_RESUME = "Записей неизвестного формата: {}."
