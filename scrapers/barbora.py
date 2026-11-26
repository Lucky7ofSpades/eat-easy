
"""Barbora (new Remix layout, v2.x): products live in window.__remixContext,
in a list called `inventories`.
"""

import json

from typing import Any
from .common import get_html


BASE = "https://barbora.lt"
MARKER = "window.__remixContext ="


def _find_key(o: Any, key: str) -> dict[str, Any] | None:
    """Walk nested data and return the first dict that has key."""

    if isinstance(o, dict):
        if key in o:
            return o

        for v in o.values():
            hit = _find_key(v, key)
            if hit is not None:
                return hit

    elif isinstance(o, list):
        for v in o:
            hit = _find_key(v, key)
            if hit is not None:
                return hit

    return None


def _parse_page(
    html: str,
) -> tuple[list[dict[str, Any]], int | None]:
    """Return (list_of_raw_products, total_count)."""

    i = html.find(MARKER)

    if i == -1:
        raise ValueError(
            "window.__remixContext not found: layout changed, or blocked?"
        )

    i += len(MARKER)

    while i < len(html) and html[i].isspace():
        i += 1

    ctx, _ = json.JSONDecoder().raw_decode(html, i)

    parent = _find_key(ctx, "inventories")

    if parent is None:
        raise ValueError(
            "'inventories' not found inside __remixContext"
        )

    return parent["inventories"], parent.get("count")


def _split_category(
    path: str | None,
) -> tuple[str | None, str | None]:
    """Split category path into readable path and short ID."""

    parts = [s for s in (path or "").split("/") if s]

    if len(parts) >= 2 and parts[0] == "c":
        return "/".join(parts[2:]) or None, parts[1]

    return "/".join(parts) or None, None


def _normalize(p: dict[str, Any]) -> dict[str, Any]:
    """Convert a raw Barbora product into a standard product record."""

    promo = p.get("promotion")
    cu = p.get("comparativeUnit") or {}

    category, category_id = _split_category(
        p.get("categoryPathUrl")
    )

    # --------------------------------------------------
    # Product prices
    # --------------------------------------------------

    current_price = p["price"]

    regular_price = (
        promo["oldPrice"]
        if promo and promo.get("oldPrice") is not None
        else current_price
    )

    on_promo = promo is not None

    loyalty_card_required = bool(
        promo and promo.get("loyaltyCardRequired")
    )

    # --------------------------------------------------
    # Comparative unit prices
    # --------------------------------------------------

    unit_price = cu.get("price")
    unit = cu.get("type")

    # Standardise measurement units
    if isinstance(unit, str):
        unit = unit.lower().strip().rstrip(".")

        if unit in ("units", "vnt"):
            unit = "pcs"

    # Ordinary products have identical comparative prices.
    # For promotions, the regular comparative price
    # is not explicitly available in our current data.
    regular_unit_price = (
        unit_price if not on_promo else None
    )

    # --------------------------------------------------
    # Final product record
    # --------------------------------------------------

    return {
        "store": "barbora",
        "id": p["id"],
        "name": p["title"],
        "brand": p.get("brand"),

        "price": current_price,
        "regular_price": regular_price,
        "loyalty_card_required": loyalty_card_required,
        "on_promo": on_promo,

        "unit_price": unit_price,
        "regular_unit_price": regular_unit_price,
        "unit": unit,

        "category": category,
        "category_id": (
            category_id or p.get("categoryShortId")
        ),
        "image": p.get("image"),
        "url": f"{BASE}/produktai/" + p["url"],
    }


def scrape(
    category_path: str,
    max_pages: int = 3,
) -> list[dict[str, Any]]:
    """Return collected products, keeping partial results on errors."""

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    for page in range(1, max_pages + 1):

        # Download and parse the page
        try:
            html = get_html(
                f"{BASE}/{category_path}",
                params={"page": page},
            )

            raw, total = _parse_page(html)

        except Exception as e:
            print(
                f"barbora page {page} FAILED: {e!r}"
                f" -> stopping, keeping {len(rows)} rows"
            )
            break

        # Normalise products
        items = []

        for p in raw:
            try:
                items.append(_normalize(p))

            except Exception as e:
                print(
                    f"barbora page {page}: "
                    f"skipped a product ({e!r})"
                )

        new = [
            r for r in items
            if r["id"] not in seen
        ]

        print(
            f"barbora page {page}: "
            f"{len(items)} products, "
            f"{len(new)} new "
            f"(category total: {total})"
        )

        if not new:
            break

        seen.update(r["id"] for r in new)
        rows += new

        if total and len(seen) >= total:
            break

    return rows
