"""
Generates criteria.yaml from mode_profiles.yaml.

Each mode profile defines human-readable keywords, locations, and toggles.
This module cross-joins them into the per-source query format that the
scout runner expects.
"""

from __future__ import annotations

import yaml

# ---------------------------------------------------------------------------
# Country → GlobalJobs region slug
# ---------------------------------------------------------------------------

COUNTRY_TO_GLOBALJOBS_REGION: dict[str, str] = {
    # APAC
    "singapore": "asia-pacific",
    "australia": "asia-pacific",
    "new zealand": "asia-pacific",
    "hong kong": "asia-pacific",
    "japan": "asia-pacific",
    "south korea": "asia-pacific",
    "korea": "asia-pacific",
    "malaysia": "asia-pacific",
    "thailand": "asia-pacific",
    "vietnam": "asia-pacific",
    "philippines": "asia-pacific",
    "indonesia": "asia-pacific",
    "china": "asia-pacific",
    "taiwan": "asia-pacific",
    # North America
    "united states": "north-america",
    "usa": "north-america",
    "canada": "north-america",
    # Europe
    "france": "europe",
    "netherlands": "europe",
    "sweden": "europe",
    "denmark": "europe",
    "finland": "europe",
    "belgium": "europe",
    "germany": "europe",
    "switzerland": "europe",
    "united kingdom": "europe",
    "uk": "europe",
    "ireland": "europe",
    "luxembourg": "europe",
    "norway": "europe",
    "austria": "europe",
    "spain": "europe",
    "portugal": "europe",
    "italy": "europe",
    # Africa / Middle East / Latin America
    "kenya": "africa",
    "nigeria": "africa",
    "south africa": "africa",
    "ethiopia": "africa",
    "brazil": "latin-america",
    "mexico": "latin-america",
    "colombia": "latin-america",
    "uae": "middle-east",
    "united arab emirates": "middle-east",
    "saudi arabia": "middle-east",
}


def _globaljobs_region(country: str) -> str:
    return COUNTRY_TO_GLOBALJOBS_REGION.get(country.lower().strip(), "")


def _is_canada(country: str) -> bool:
    return country.lower().strip() == "canada"


def _is_us(country: str) -> bool:
    return country.lower().strip() in ("united states", "usa", "us")


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

def generate_criteria(
    profiles_path: str = "config/mode_profiles.yaml",
    output_path: str = "config/criteria.yaml",
) -> dict:
    """
    Read mode_profiles.yaml and write a fully-formed criteria.yaml.
    Returns the generated config dict.
    """
    with open(profiles_path, encoding="utf-8") as f:
        profiles = yaml.safe_load(f)

    output: dict = {"modes": {}}

    for mode_id, profile in profiles.get("modes", {}).items():
        keywords: list[str] = profile.get("keywords", [])
        locations: list[dict] = profile.get("locations", [])
        suffix: str = profile.get("search_suffix", "")
        sources: dict = profile.get("sources", {})
        gh_companies: list[dict] = profile.get("greenhouse_companies", [])
        gh_filters: list[str] = profile.get("greenhouse_title_filters", [])

        mode_cfg: dict = {
            "label": profile.get("label", mode_id),
            "description": profile.get("description", ""),
        }

        # ---- SerpAPI (Google Jobs) ----------------------------------------
        if sources.get("serpapi"):
            serpapi_queries = []
            for kw in keywords:
                for loc in locations:
                    q = f"{kw} {suffix}".strip() if suffix else kw
                    serpapi_queries.append({
                        "q": q,
                        "location": loc["name"],
                        "country": loc["country"],
                        "region": _globaljobs_region(loc["country"]).upper().replace("-", "_") or "OTHER",
                    })
            mode_cfg["serpapi_queries"] = serpapi_queries
        else:
            mode_cfg["serpapi_queries"] = []

        # ---- MyCareersFuture (Singapore) ------------------------------------
        if sources.get("mcf"):
            mode_cfg["mcf_queries"] = [
                {"search": kw, "max_pages": 3} for kw in keywords
            ]
        else:
            mode_cfg["mcf_queries"] = []

        # ---- Jaabz ----------------------------------------------------------
        if sources.get("jaabz"):
            jaabz_queries = []
            seen = set()
            for kw in keywords:
                for loc in locations:
                    key = (kw, loc["country"])
                    if key in seen:
                        continue
                    seen.add(key)
                    jaabz_queries.append({
                        "keyword": kw,
                        "location": loc["country"],
                        "max_pages": 2,
                    })
            mode_cfg["jaabz_queries"] = jaabz_queries
        else:
            mode_cfg["jaabz_queries"] = []

        # ---- GlobalJobs -----------------------------------------------------
        if sources.get("globaljobs"):
            gj_queries = []
            seen_regions: set[str] = set()
            for loc in locations:
                region_slug = _globaljobs_region(loc["country"])
                if region_slug:
                    seen_regions.add(region_slug)
            for kw in keywords:
                for region_slug in sorted(seen_regions):
                    gj_queries.append({
                        "keyword": kw,
                        "region": region_slug,
                        "max_pages": 2,
                    })
            mode_cfg["globaljobs_queries"] = gj_queries
        else:
            mode_cfg["globaljobs_queries"] = []

        # ---- USAJobs --------------------------------------------------------
        if sources.get("usajobs"):
            mode_cfg["usajobs_queries"] = [
                {"keyword": kw, "results_per_page": 25} for kw in keywords
            ]
        else:
            mode_cfg["usajobs_queries"] = []

        # ---- Job Bank Canada ------------------------------------------------
        if sources.get("jobbank"):
            canada_locs = [loc for loc in locations if _is_canada(loc["country"])]
            if canada_locs:
                jb_queries = []
                seen = set()
                for kw in keywords:
                    for loc in canada_locs:
                        key = (kw, loc["country"])
                        if key in seen:
                            continue
                        seen.add(key)
                        jb_queries.append({
                            "keyword": kw,
                            "location": loc["country"],
                            "max_pages": 3,
                        })
                mode_cfg["jobbank_queries"] = jb_queries
            else:
                mode_cfg["jobbank_queries"] = []
        else:
            mode_cfg["jobbank_queries"] = []

        # ---- IT Job Board USA -----------------------------------------------
        if sources.get("itjobboard"):
            mode_cfg["itjobboard_queries"] = [
                {"keyword": kw, "location": "United States"} for kw in keywords
            ]
        else:
            mode_cfg["itjobboard_queries"] = []

        # ---- Indeed EU (Mode C) ---------------------------------------------
        if sources.get("indeed"):
            indeed_queries = []
            for kw in keywords:
                for loc in locations:
                    domain = loc.get("indeed_domain")
                    if not domain:
                        continue
                    indeed_queries.append({
                        "q": kw,
                        "location": loc["name"],
                        "country": loc["country"],
                        "domain": domain,
                        "region": "OTHER",
                    })
            mode_cfg["indeed_queries"] = indeed_queries
        else:
            mode_cfg["indeed_queries"] = []

        # ---- Greenhouse -----------------------------------------------------
        if sources.get("greenhouse") and gh_companies:
            mode_cfg["greenhouse_companies"] = gh_companies
            mode_cfg["greenhouse_title_filters"] = gh_filters
        else:
            mode_cfg["greenhouse_companies"] = []
            mode_cfg["greenhouse_title_filters"] = []

        output["modes"][mode_id] = mode_cfg

    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(output, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

    return output


if __name__ == "__main__":
    generate_criteria()
    print("criteria.yaml regenerated from mode_profiles.yaml")
