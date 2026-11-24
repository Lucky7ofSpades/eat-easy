"""Rimi: each product is an HTML card <li class="product-grid__item">
with a JSON blob in data-gtm-eec-product and the unit price in the visible text."""
import json, re
from typing import Any
from bs4 import BeautifulSoup
from .common import get_html

BASE = "https://www.rimi.lt"
UNIT_PRICE = re.compile(r"Kaina už vienetą:\s*(\d+(?:[ \d]*)?,\d+)\s*€/(\w+)")
DISCOUNT = re.compile(r"-\s*(\d+)\s*%")
PRICE_PATTERN = re.compile(r"(\d+)\s+(\d{2})\s*€")
REGULAR_PRICE = re.compile(
    r"Įprasta kaina:\s*(\d+[.,]\d{2})\s*€"
)


def _parse_page(html: str) -> list[dict[str, Any]]:
    rows = []
    for card in BeautifulSoup(html, "html.parser").select("li.product-grid__item"):
        div = card.select_one("div[data-gtm-eec-product]")
        if div is None:
            continue
        info = json.loads(div["data-gtm-eec-product"])

        text = card.get_text(" ", strip=True)

        discount_match = DISCOUNT.search(text)
        regular_match = REGULAR_PRICE.search(text)

        discount_pct = (
            int(discount_match.group(1))
            if discount_match else None
        )

        requires_rimi_card = card.select_one(
            'img[src*="promotion-labels/rimi-card"]'
        ) is not None

        gtm_price = float(info["price"])

        if regular_match:
            # Regular promotion: GTM already contains current price
            regular_price = float(
                regular_match.group(1).replace(",", ".")
            )
            current_price = gtm_price

        elif discount_match:
            # Percentage promotion: GTM contains regular price
            regular_price = gtm_price

            price_label = card.select_one(".price-label")
            price_text = (
                price_label.get_text(" ", strip=True)
                if price_label else ""
            )

            price_match = PRICE_PATTERN.search(price_text)

            current_price = (
                float(f"{price_match.group(1)}.{price_match.group(2)}")
                if price_match else None
            )

        else:
            # No promotion detected
            regular_price = None
            current_price = gtm_price

        on_promo = bool(regular_match or discount_match)

        promo_price = current_price if on_promo else None

        m = UNIT_PRICE.search(card.get_text(" ", strip=True))
        unit_price = float(m.group(1).replace(" ", "").replace(",", ".")) if m else None

        a = card.select_one("a.card__url")
        href = a["href"] if a else None
        img = card.select_one("img")
        category = href.split("/produktai/")[1].split("/p/")[0] if href and "/produktai/" in href else None

        rows.append({
            "store": "rimi",
            "id": info["id"],
            "name": info["name"],
            "brand": "RIMI" if "RIMI" in info["name"] else info.get("brand"),

            "price": current_price,
            "regular_price": regular_price if on_promo else current_price,
            "loyalty_card_required": bool(requires_rimi_card),
            "on_promo": on_promo,

            "unit_price": unit_price,
            "unit": m.group(2) if m else None,
            "category": category,
            "image": img.get("src") if img else None,
            "url": BASE + href if href else None,
        })
    return rows


def scrape(code: str, slug: str, max_pages: int = 3) -> list[dict[str, Any]]:
    """code example: 'SH-9', slug example: 'mesa-ir-zuvis-'"""
    url = f"{BASE}/e-parduotuve/lt/produktai/{slug}/c/{code}"
    rows, seen = [], set()
    for page in range(1, max_pages + 1):
        params = {
            "currentPage": page,
            "pageSize": 40,
            "query": f":relevance:allCategories:{code}:assortmentStatus:inAssortment",
        }
        items = _parse_page(get_html(url, params=params))
        new = [r for r in items if r["id"] not in seen]
        print(f"rimi page {page}: {len(items)} cards, {len(new)} new")
        if not new:
            break
        seen.update(r["id"] for r in new)
        rows += new
    return rows
