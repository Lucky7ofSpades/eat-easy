import time
import requests

BASE_URL = "https://jaukusskoniai.lt/api/recipes"


def fetch_catalogue(max_pages=5, delay=2):
    all_recipes = []
    seen_cursors = set()
    cursor = None

    for page in range(max_pages):
        params = {"cursor": cursor} if cursor else {}

        response = requests.get(
            BASE_URL,
            params=params,
            timeout=20
        )
        response.raise_for_status()

        data = response.json()
        recipes = data["recipes"]

        all_recipes.extend(recipes)

        print(f"Page {page + 1}: {len(recipes)} recipes")

        if not data["hasMore"]:
            break

        next_cursor = data.get("nextCursor")

        if not next_cursor or next_cursor in seen_cursors:
            print("Pagination stopped: missing or repeated cursor")
            break

        seen_cursors.add(next_cursor)
        cursor = next_cursor

        time.sleep(delay)

    return all_recipes


def fetch_recipe(slug):
    url = f"{BASE_URL}/{slug}"

    response = requests.get(url, timeout=20)
    response.raise_for_status()

    data = response.json()

    if data.get("subscriberOnly") or data.get("locked"):
        return None

    return data


def collect_recipes(slugs, delay=2):
    recipes = []
    failed = []

    for i, slug in enumerate(slugs, start=1):
        try:
            data = fetch_recipe(slug)

            if data is not None:
                recipes.append(data)
                print(f"[{i}/{len(slugs)}] Collected: {slug}")
            else:
                print(f"[{i}/{len(slugs)}] Restricted: {slug}")

        except requests.RequestException as e:
            failed.append(slug)
            print(f"Failed: {slug}: {e}")

            # Stop rather than repeatedly requesting a blocked API.
            if getattr(e.response, "status_code", None) in (403, 429):
                break

        time.sleep(delay)

    return recipes, failed