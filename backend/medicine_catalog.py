"""Small RxNorm name-search adapter. It never recommends dosing."""
from __future__ import annotations

from functools import lru_cache

import httpx

RXNORM_SEARCH_URL = "https://rxnav.nlm.nih.gov/REST/approximateTerm.json"


class MedicineCatalogUnavailable(RuntimeError):
    pass


@lru_cache(maxsize=256)
def suggest_medicines(query: str) -> list[dict[str, str]]:
    term = query.strip()
    if len(term) < 3:
        return []
    try:
        response = httpx.get(
            RXNORM_SEARCH_URL,
            params={"term": term, "maxEntries": 10, "option": 1},
            headers={"User-Agent": "DermScope-development/1.0"},
            timeout=6,
        )
        response.raise_for_status()
        candidates = response.json().get("approximateGroup", {}).get("candidate") or []
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        raise MedicineCatalogUnavailable("Medicine-name suggestions are temporarily unavailable") from exc

    suggestions: list[dict[str, str]] = []
    seen: set[str] = set()
    for candidate in candidates:
        name = str(candidate.get("name") or "").strip()
        rxcui = str(candidate.get("rxcui") or "").strip()
        key = name.casefold()
        if not name or not rxcui or key in seen:
            continue
        seen.add(key)
        suggestions.append({"name": name, "rxcui": rxcui})
        if len(suggestions) == 8:
            break
    return suggestions
