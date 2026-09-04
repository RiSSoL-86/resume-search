MAX_PAGE_SIZE = 50
DEFAULT_PAGE_SIZE = 10
MAX_REQUIREMENTS = 20_000

EMPTY_REQUIREMENTS = "Опишите вакансию — по пустому тексту искать нечего."
LONG_REQUIREMENTS = "Требования длиннее {} символов.".format(
    f"{MAX_REQUIREMENTS:,}".replace(",", " "),
)

# One upload carries a team's export, never a whole database.
MAX_UPLOAD_BYTES = 128 * 1024 * 1024

UPLOAD_FIELD = "file"
UNREADABLE_UPLOAD = "Файл не читается ни как zip-архив, ни как JSON."
EMPTY_UPLOAD = "В файле нет ни одного резюме."
UNKNOWN_UPLOAD = "Такой загрузки нет."

MONTHS = (
    "Январь",
    "Февраль",
    "Март",
    "Апрель",
    "Май",
    "Июнь",
    "Июль",
    "Август",
    "Сентябрь",
    "Октябрь",
    "Ноябрь",
    "Декабрь",
)

YEAR_FORMS = ("год", "года", "лет")
MONTH_FORMS = ("месяц", "месяца", "месяцев")

CURRENCIES = {"RUR": "₽", "RUB": "₽", "USD": "$", "EUR": "€"}

TEMPLATE = "resumes/dashboard.html"
FORM_TEMPLATE = "resumes/search.html"
PLAN_TEMPLATE = "resumes/plan.html"
FALLBACK = "resumes"

# Where the edited criteria are sent; the panel is shown on two pages.
PLAN_ACTION = "/api/resumes/plan/"

# Every list of criteria the panel lets a recruiter tick off, in order.
PLAN_GROUPS = (
    ("must", "must_keywords", "Технологии от рекрутёра"),
    ("required", "required_keywords", "Ключевые термины вакансии"),
    ("roles", "professional_roles", "Должности"),
    ("optional", "optional_keywords", "Прочие термины"),
    ("areas", "areas", "Города"),
    ("formats", "work_formats", "Формат работы"),
    ("employments", "employments", "Занятость"),
    ("education", "education_levels", "Образование"),
    ("languages", "languages", "Языки"),
)

# The criteria that are one number rather than a list, and how they read.
PLAN_LIMITS = (
    ("experience", "min_experience_years", "Стаж от {} лет"),
    ("tenure", "min_tenure_months", "От {} месяцев на одном месте"),
    ("salary", "max_salary", "Зарплата до {} ₽"),
)

# The weights the recruiter moves, in the order they are drawn.
PLAN_SLIDERS = (
    (
        "technology",
        "Технологии",
        "Сколько названных технологий подтверждено описанием работы.",
    ),
    (
        "semantic",
        "Смысл опыта",
        "Насколько описанная работа похожа на вакансию по существу.",
    ),
    (
        "lexical",
        "Слова резюме",
        "Совпадение вакансии с текстом резюме слово в слово.",
    ),
    (
        "role",
        "Стаж в должности",
        "Годы, отработанные именно в искомой роли.",
    ),
    (
        "preference",
        "Пожелания",
        "Город, формат, образование, язык, зарплата, усидчивость.",
    ),
)

WORK_FORMAT_NAMES = {
    "REMOTE": "Удалённо",
    "ON_SITE": "В офисе",
    "HYBRID": "Гибрид",
    "FIELD_WORK": "Разъездная",
}
EMPLOYMENT_NAMES = {
    "full": "Полная",
    "part": "Частичная",
    "project": "Проектная",
    "probation": "Стажировка",
    "volunteer": "Волонтёрство",
}
EDUCATION_NAMES = {
    "secondary": "Среднее",
    "special_secondary": "Среднее специальное",
    "unfinished_higher": "Неоконченное высшее",
    "higher": "Высшее",
    "bachelor": "Бакалавр",
    "master": "Магистр",
    "candidate": "Кандидат наук",
    "doctor": "Доктор наук",
}
LANGUAGE_NAMES = {
    "rus": "Русский",
    "eng": "Английский",
    "deu": "Немецкий",
    "fra": "Французский",
    "spa": "Испанский",
    "ita": "Итальянский",
    "zho": "Китайский",
}

# Which name dictionary reads the codes of which group.
PLAN_NAMES = {
    "formats": WORK_FORMAT_NAMES,
    "employments": EMPLOYMENT_NAMES,
    "education": EDUCATION_NAMES,
}
