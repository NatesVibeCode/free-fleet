"""Multi-source entity bundler.

Combines raw evidence hits gathered across web crawls, case studies, vendor partner
registries, B2B review platforms, community/social footprints, and ATS job postings
into consolidated, section-tagged composite dossiers per canonical entity.
"""
from __future__ import annotations

import csv
import re
from collections import defaultdict
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .models import InputItem

# Known directory & platform domains mapped to source categories
REGISTRY_DOMAINS = (
    "partners.amazonaws.com",
    "snowflake.com",
    "appsource.microsoft.com",
    "cloud.google.com",
    "datadoghq.com",
    "ecosystem.hubspot.com",
    "salesforce.com",
)

REVIEW_DOMAINS = (
    "clutch.co",
    "g2.com",
    "goodfirms.co",
    "themanifest.com",
    "upcity.com",
)

COMMUNITY_DOMAINS = (
    "github.com",
    "youtube.com",
    "substack.com",
    "medium.com",
    "dev.to",
    # The community backends the fleet searches. Without these, an HN thread or
    # a Reddit post was filed as `general_web` and — in the sourcing runner —
    # could be mistaken for a partner domain.
    "news.ycombinator.com",
    "reddit.com",
    "redd.it",
    "stackoverflow.com",
    "stackexchange.com",
    "serverfault.com",
    "superuser.com",
    "lobste.rs",
    "lemmy.world",
    "lemmy.ml",
    "programming.dev",
)

ATS_DOMAINS = (
    "jobs.ashbyhq.com",
    "boards.greenhouse.io",
    "jobs.lever.co",
    "apply.workable.com",
    "jobs.",
)

CASE_STUDY_PATH_RE = re.compile(r"/(case-stud|work|customers?|success-stor|clients|portfolio)", re.IGNORECASE)
PRACTICE_PATH_RE = re.compile(r"/(services?|solutions?|practices?|about|partners?|consulting)", re.IGNORECASE)


def canonicalize_entity_id(identifier_or_url: str) -> str:
    """Extract clean, canonical domain/entity id from a URL or raw identifier."""
    raw = (identifier_or_url or "").strip().lower()
    if not raw:
        return "unknown_entity"

    # If it contains a URL scheme or looks like a URL
    if "://" in raw or "/" in raw:
        parsed = urlparse(raw if "://" in raw else f"https://{raw}")
        host = parsed.netloc.lower().strip()
        path = parsed.path.strip("/")

        # Strip common prefixes
        if host.startswith("www."):
            host = host[4:]

        # Handle ATS URLs where company slug is the first path segment
        if any(ats in host for ats in ("ashbyhq.com", "greenhouse.io", "lever.co", "workable.com")):
            parts = [p for p in path.split("/") if p]
            if parts:
                slug = parts[0].replace("-", "_")
                # Append .com if slug looks like a domain name
                return f"{slug}.com" if "." not in slug else slug

        # Handle vendor registry paths: e.g. partners.amazonaws.com/partners/trace3
        if "partners.amazonaws.com" in host or "snowflake.com" in host:
            parts = [p for p in path.split("/") if p and p not in ("partners", "en-us", "marketplace")]
            if parts:
                slug = parts[-1].replace("-", "_")
                return f"{slug}.com" if "." not in slug else slug

        # Handle Clutch/G2 profiles: clutch.co/profile/trace3
        if any(rev in host for rev in ("clutch.co", "g2.com")):
            parts = [p for p in path.split("/") if p and p not in ("profile", "it-services", "products")]
            if parts:
                slug = parts[-1].replace("-", "_")
                return f"{slug}.com" if "." not in slug else slug

        if host:
            return host

    # Plain text identifier
    cleaned = re.sub(r"[^a-z0-9_.-]+", "_", raw).strip("_.")
    return cleaned or "unknown_entity"


def classify_source_category(source_uri: str, entity_id: str = "") -> str:
    """Classify a source URL into one of the 6 canonical partner evidence categories."""
    uri = (source_uri or "").strip().lower()
    if not uri:
        return "general_web"

    # 1. Vendor registries
    if any(d in uri for d in REGISTRY_DOMAINS) and "partner" in uri:
        return "vendor_registry"

    # 2. Review and audit platforms
    if any(d in uri for d in REVIEW_DOMAINS):
        return "b2b_directory_audit"

    # 3. Community and social platforms
    if any(d in uri for d in COMMUNITY_DOMAINS):
        return "community_and_social"

    # 4. ATS / Hiring requisitions
    if any(ats in uri for ats in ATS_DOMAINS):
        return "ats_requisitions"

    # 5. First-party case studies
    if CASE_STUDY_PATH_RE.search(uri):
        return "first_party_case_study"

    # 6. First-party practices and services
    if PRACTICE_PATH_RE.search(uri):
        return "first_party_practice"

    # Fallback to first-party if host matches entity domain
    if entity_id and entity_id in uri:
        return "first_party_practice"

    return "general_web"


def bundle_records(
    records: Iterable[InputItem | dict[str, Any]],
    *,
    min_sources: int = 1,
    min_categories: int = 1,
) -> list[InputItem]:
    """Group multi-channel evidence hits by canonical entity into composite dossiers."""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for item in records:
        if isinstance(item, InputItem):
            raw_id = item.item_id
            text = item.text
            uri = item.source_uri or ""
            metadata = dict(item.metadata or {})
        else:
            raw_id = str(item.get("item_id") or item.get("domain") or item.get("url") or "")
            text = str(item.get("text") or item.get("research") or "")
            uri = str(item.get("source_uri") or item.get("url") or "")
            metadata = dict(item.get("metadata") or {})

        canonical_id = canonicalize_entity_id(raw_id or uri)
        category = metadata.get("source_category") or classify_source_category(uri, canonical_id)

        grouped[canonical_id].append({
            "text": text.strip(),
            "source_uri": uri,
            "source_category": category,
            "metadata": metadata,
        })

    bundled_items: list[InputItem] = []

    for entity_id, hits in sorted(grouped.items()):
        if len(hits) < min_sources:
            continue

        categories = sorted({h["source_category"] for h in hits if h["source_category"]})
        if len(categories) < min_categories:
            continue

        # Format composite document
        sections: list[str] = [f"# Multi-Source Evidence Dossier: {entity_id}\n"]
        all_uris: list[str] = []

        for i, hit in enumerate(hits, 1):
            cat = hit["source_category"].upper()
            uri_text = hit["source_uri"] or f"source_{i}"
            all_uris.append(uri_text)
            sections.append(
                f"=== SECTION: {cat} (URI: {uri_text}) ===\n"
                f"{hit['text']}\n"
            )

        composite_text = "\n".join(sections).strip()

        bundled_items.append(
            InputItem(
                item_id=entity_id,
                text=composite_text,
                source_uri=all_uris[0] if all_uris else "",
                title=f"Partner Dossier: {entity_id}",
                metadata={
                    "entity": entity_id,
                    "source_count": len(hits),
                    "source_categories": categories,
                    "category_count": len(categories),
                    "source_uris": all_uris,
                },
            )
        )

    return bundled_items


def load_and_bundle(
    input_path: str | Path,
    *,
    id_column: str | None = None,
    text_column: str | None = None,
    uri_column: str | None = None,
    min_sources: int = 1,
    min_categories: int = 1,
) -> list[InputItem]:
    """Load records from CSV or JSONL and bundle by canonical entity."""
    from .input_data import load_input_items

    raw_items = load_input_items(
        input_path,
        id_column=id_column,
        text_column=text_column,
        uri_column=uri_column,
    )
    return bundle_records(raw_items, min_sources=min_sources, min_categories=min_categories)


def export_bundled_csv(
    bundled_items: Sequence[InputItem],
    output_path: str | Path,
) -> Path:
    """Export bundled items to a CSV file ready for harness-fleet run."""
    out = Path(output_path).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["item_id", "text", "source_uri", "source_count", "source_categories"])
        for item in bundled_items:
            meta = item.metadata or {}
            writer.writerow([
                item.item_id,
                item.text,
                item.source_uri or "",
                meta.get("source_count", 1),
                ",".join(meta.get("source_categories", [])),
            ])
    return out
