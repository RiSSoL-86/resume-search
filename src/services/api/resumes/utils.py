from datetime import date
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from asgiref.sync import sync_to_async
from django.http import HttpRequest, HttpResponse
from django.template.loader import render_to_string

from services.api.resumes.constants import (
    CURRENCIES,
    FALLBACK,
    MONTH_FORMS,
    MONTHS,
    YEAR_FORMS,
)

if TYPE_CHECKING:
    from http import HTTPStatus


async def render_html(
    status: HTTPStatus,
    context: dict[str, Any],
    template_name: str,
    download_name: str = "",
    request: HttpRequest | None = None,
) -> HttpResponse:
    """Render a template to HTML.

    When ``download_name`` is given the response is served as an attachment
    named ``<download_name>.html``; otherwise it is returned inline.
    """
    html = await sync_to_async(
        func=render_to_string,
        thread_sensitive=False,
    )(template_name, context=context, request=request)
    response = HttpResponse(
        html,
        status=status,
        content_type="text/html; charset=utf-8",
    )
    if download_name:
        encoded = quote(f"{download_name}.html")
        # A Russian name leaves nothing but punctuation behind in ASCII.
        ascii_name = "".join(
            symbol
            for symbol in download_name
            if symbol.isascii() and (symbol.isalnum() or symbol in " -_")
        ).strip()
        fallback = f"{ascii_name or FALLBACK}.html"
        response["Content-Disposition"] = (
            f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{encoded}"
        )
    return response


def plural(value: int, forms: tuple[str, str, str]) -> str:
    """Return the noun form agreeing with a number in Russian."""
    # Teens all take the third form, whatever their last digit is.
    if value % 100 // 10 == 1:
        return forms[2]

    last = value % 10
    if last == 1:
        return forms[0]
    if 2 <= last <= 4:  # noqa: PLR2004
        return forms[1]
    return forms[2]


def format_duration(months: int | None) -> str:
    """Return a month count as "5 лет 1 месяц"."""
    if not months:
        return ""

    years, rest = divmod(months, 12)
    parts = []
    if years:
        parts.append(f"{years} {plural(value=years, forms=YEAR_FORMS)}")
    if rest:
        parts.append(f"{rest} {plural(value=rest, forms=MONTH_FORMS)}")
    return " ".join(parts)


def format_month(value: str | None) -> str:
    """Return an ISO date as "Август 2023"."""
    if not value:
        return ""

    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return value
    return f"{MONTHS[parsed.month - 1]} {parsed.year}"


def format_period(start: str | None, end: str | None) -> str:
    """Return the period line of one job."""
    opened = format_month(value=start)
    if not opened:
        return ""
    return f"{opened} — {format_month(value=end) or 'по настоящее время'}"


def format_salary(amount: int | None, currency: str | None) -> str:
    """Return the salary expectation as one line."""
    if not amount:
        return ""

    sign = CURRENCIES.get(currency or "", currency or "")
    return f"{amount:,}".replace(",", " ") + (f" {sign}" if sign else "")
