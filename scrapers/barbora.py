"""Barbora (new Remix layout, v2.x): products live in window.__remixContext,
in a list called `inventories`."""
import json
from typing import Any
from .common import get_html

BASE = "https://barbora.lt"
MARKER = "window.__remixContext ="


def _find_key(o: Any, key: str) -> dict[str, Any] | None:
    """Walk nested data and return the value of the first dict that has `key`."""
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


def _parse_page(html: str) -> tuple[list[dict[str, Any]], int | None]:
    """Return (list_of_raw_products, total_count). Raises if the layout changed."""
    i = html.find(MARKER)
    if i == -1:
        raise ValueError("window.__remixContext not found: layout changed, or blocked?")
    i += len(MARKER)
    while html[i].isspace():
        i += 1
    ctx, _ = json.JSONDecoder().raw_decode(html, i)

    parent = _find_key(ctx, "inventories")
    if parent is None:
        raise ValueError("'inventories' not found inside __remixContext")
    return parent["inventories"], parent.get("count")


def _normalize(p: dict[str, Any]) -> dict[str, Any]:
    promo = p.get("promotion")
    cu = p.get("comparativeUnit") or {}
    return {
        "store": "barbora",
        "id": p["id"],
        "name": p["title"],
        "brand": p.get("brand"),

        "price": p["price"],
        "regular_price": promo["oldPrice"] if promo and promo.get("oldPrice") is not None else p["price"],
        "loyalty_card_required": bool(promo and promo.get("loyaltyCardRequired")),
        "on_promo": promo is not None,

        "unit_price": cu.get("price"),
        "unit": cu.get("type"),
        "category": p.get("categoryPathUrl"),
        "image": p.get("image"),
        "url": f"{BASE}/produktai/" + p["url"],
    }


def scrape(category_path: str, max_pages: int = 3) -> list[dict[str, Any]]:
    """category_path example:
    'c/LVOK/mesa-zuvis-ir-kulinarija/sviezia-mesa-ir-paukstiena'"""
    rows, seen = [], set()
    for page in range(1, max_pages + 1):
        html = get_html(f"{BASE}/{category_path}", params={"page": page})
        raw, total = _parse_page(html)
        items = [_normalize(p) for p in raw]
        new = [r for r in items if r["id"] not in seen]
        print(f"barbora page {page}: {len(items)} products, {len(new)} new (category total: {total})")
        if not new:      # empty page, or the site ignored ?page= and repeated page 1
            break
        seen.update(r["id"] for r in new)
        rows += new
    return rows