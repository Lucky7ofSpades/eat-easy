
"""Rimi: each product is an HTML card <li class="product-grid__item">
with embedded GTM JSON and structured regular/promotional prices.
"""

import json
import re

from typing import Any
from bs4 import BeautifulSoup, Tag
from .common import get_html


BASE = "https://www.rimi.lt"

UNIT_PRICE = re.compile(
    r"(\d+(?:[\s\d]*\d)?(?:[.,]\d+)?)\s*€\s*/\s*(kg|l|vnt\.?|pcs|units)\b",
    re.IGNORECASE,
)

REGULAR_PRICE = re.compile(
    r"Įprasta kaina:\s*(\d+[.,]\d{2})\s*€"
)

PRICE_PATTERN = re.compile(
    r"(\d+)\s+(\d{2})\s*€"
)


def _parse_number(value: str) -> float:
    """Convert a Lithuanian-formatted number into a float."""
    return float(
        re.sub(r"\s+", "", value).replace(",", ".")
    )


def _parse_unit_price(
    text: str,
) -> tuple[float | None, str | None]:
    """Extract comparative price and standardised measurement unit."""

    match = UNIT_PRICE.search(text)

    if not match:
        return None, None

    price = _parse_number(match.group(1))
    unit = match.group(2).lower().rstrip(".")

    if unit in ("vnt", "units"):
        unit = "pcs"

    return price, unit


def _extract_promo_price(card: Tag) -> float | None:
    """Extract advertised promotional price from the price label."""

    price_label = card.select_one(".price-label__price")

    if price_label is None:
        return None

    major = price_label.select_one(".major")
    cents = price_label.select_one(".cents")

    if major is not None and cents is not None:
        return _parse_number(
            f"{major.get_text(strip=True)}."
            f"{cents.get_text(strip=True)}"
        )

    # Fallback for alternative price label formatting
    text = price_label.get_text(" ", strip=True)
    match = PRICE_PATTERN.search(text)

    if match:
        return float(
            f"{match.group(1)}.{match.group(2)}"
        )

    return None


def _parse_card(card: Tag) -> dict[str, Any] | None:
    """Turn one product card into a normalised product record."""

    div = card.select_one("div[data-gtm-eec-product]")

    if div is None:
        return None

    info = json.loads(div["data-gtm-eec-product"])

    text = card.get_text(" ", strip=True)

    gtm_price = float(info["price"])

    # Detect loyalty card requirement
    requires_rimi_card = card.select_one(
        'img[src*="promotion-labels/rimi-card"]'
    ) is not None

    # Extract explicitly displayed regular price
    regular_match = REGULAR_PRICE.search(text)

    # Extract promotional price directly from HTML
    promo_price = _extract_promo_price(card)

    # --------------------------------------------------
    # Product price
    # --------------------------------------------------

    if regular_match:
        # Explicit regular price is available.
        regular_price = _parse_number(
            regular_match.group(1)
        )

        current_price = (
            promo_price
            if promo_price is not None
            else gtm_price
        )

    elif promo_price is not None:
        # Separate promotional label, including loyalty offers.
        regular_price = gtm_price
        current_price = promo_price

    else:
        # Ordinary product without a separate promotional price.
        regular_price = gtm_price
        current_price = gtm_price

    on_promo = current_price < regular_price

    # --------------------------------------------------
    # Comparative unit prices
    # --------------------------------------------------

    base_unit_element = card.select_one(
        ".card__price-per .sr-only"
    )

    # Fallback when the accessible text is absent
    if base_unit_element is None:
        base_unit_element = card.select_one(
            ".card__price-per"
        )

    base_unit_text = (
        base_unit_element.get_text(" ", strip=True)
        if base_unit_element is not None
        else ""
    )

    base_unit_price, base_unit = _parse_unit_price(
        base_unit_text
    )

    promo_unit_element = card.select_one(
        ".price-label .price-per-unit"
    )

    promo_unit_text = (
        promo_unit_element.get_text(" ", strip=True)
        if promo_unit_element is not None
        else ""
    )

    promo_unit_price, promo_unit = _parse_unit_price(
        promo_unit_text
    )

    # --------------------------------------------------
    # Assign current and regular comparative prices
    # --------------------------------------------------

    if on_promo and regular_match:
        # The ordinary card may already display the
        # discounted comparative price.
        unit_price = (
            promo_unit_price
            if promo_unit_price is not None
            else base_unit_price
        )

        unit = promo_unit or base_unit

        # Do not assume the base unit price is regular
        # when an explicit regular price is displayed.
        regular_unit_price = None

    elif on_promo and promo_price is not None:
        # Separate regular and promotional price labels.
        unit_price = promo_unit_price
        regular_unit_price = base_unit_price

        unit = promo_unit or base_unit

        # A single unit field cannot represent two
        # incompatible comparative measurement units.
        if promo_unit and base_unit and promo_unit != base_unit:
            regular_unit_price = None

    else:
        # Ordinary pricing.
        unit_price = base_unit_price
        regular_unit_price = base_unit_price
        unit = base_unit

    # --------------------------------------------------
    # Product metadata
    # --------------------------------------------------

    a = card.select_one("a.card__url")
    href = a["href"] if a else None

    img = card.select_one(".card__image-wrapper img")

    category = None

    if href and "/produktai/" in href:
        product_path = (
            href.split("/produktai/", 1)[1]
            .split("/p/", 1)[0]
        )

        # Remove the final product-specific slug
        if "/" in product_path:
            category = product_path.rsplit("/", 1)[0]

    # --------------------------------------------------
    # Final product record
    # --------------------------------------------------

    return {
        "store": "rimi",
        "id": info["id"],
        "name": info["name"],
        "brand": (
            "RIMI"
            if "RIMI" in info["name"]
            else info.get("brand")
        ),

        "price": current_price,
        "regular_price": regular_price,
        "loyalty_card_required": bool(requires_rimi_card),
        "on_promo": on_promo,

        "unit_price": unit_price,
        "regular_unit_price": regular_unit_price,
        "unit": unit,

        "category": category,
        "category_id": info.get("category"),
        "image": img.get("src") if img else None,
        "url": BASE + href if href else None,
    }


def _parse_page(html: str) -> list[dict[str, Any]]:
    """Extract all valid product records from one listing page."""

    rows = []

    for card in BeautifulSoup(
        html, "html.parser"
    ).select("li.product-grid__item"):

        try:
            row = _parse_card(card)

        except Exception as e:
            print(f"rimi: skipped a card ({e!r})")
            continue

        if row is not None:
            rows.append(row)

    return rows


def scrape(
    code: str,
    slug: str,
    max_pages: int = 3,
) -> list[dict[str, Any]]:
    """Never raises on request or parsing errors.

    Returns the rows collected so far.

    code example: 'SH-9'
    slug example: 'mesa-ir-zuvis-'
    """

    url = (
        f"{BASE}/e-parduotuve/lt/"
        f"produktai/{slug}/c/{code}"
    )

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    for page in range(1, max_pages + 1):

        params = {
            "currentPage": page,
            "pageSize": 40,
            "query": (
                f":relevance:allCategories:"
                f"{code}:assortmentStatus:inAssortment"
            ),
        }

        try:
            items = _parse_page(
                get_html(url, params=params)
            )

        except Exception as e:
            print(
                f"rimi page {page} FAILED: {e!r}"
                f" -> stopping, keeping {len(rows)} rows"
            )
            break

        new = [
            r for r in items
            if r["id"] not in seen
        ]

        print(
            f"rimi page {page}: "
            f"{len(items)} cards, {len(new)} new"
        )

        if not new:
            break

        seen.update(r["id"] for r in new)
        rows += new

    return rows
