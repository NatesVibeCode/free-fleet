"""Run the partner sourcing plan: find partners, then enrich each one.

Two entry points, one pipeline:

* **find** — cold start, no list. Fans the plan's queries across every search
  backend the fleet ships (web, HN, Reddit, Stack Exchange, Discourse, dev.to,
  Lobsters, Lemmy, YC) and turns the hits into candidate partner entities.
* **enrich** — for one partner, whether it came from *find* or from a list you
  already have. Fetches their own site, their ATS board, their Clutch/G2/
  ZoomInfo pages, their vendor-registry listing, independent mentions, and
  press, then bundles everything per entity.

The rule that makes the difference between evidence and noise: **attribution**.
A hit counts toward a partner only when that partner's domain or name appears
in the URL or in the captured text. A web search for "Trace3 Kafka" happily
returns pages about *tracing*; without this filter they read as evidence.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence
from urllib.parse import urlparse

from .bundler import (
    ATS_DOMAINS,
    CASE_STUDY_PATH_RE,
    COMMUNITY_DOMAINS,
    REGISTRY_DOMAINS,
    REVIEW_DOMAINS,
    bundle_records,
    canonicalize_entity_id,
)
from .discover import (
    RawRecord,
    SearchHit,
    crawl_site,
    fetch_text,
    to_input_items,
    web_search,
)
from .models import InputItem

PLAN_PATH = Path(__file__).resolve().parent / "data" / "partner_sources.json"
COMMUNITY_BACKENDS = ("hn", "reddit", "stackexchange", "discourse", "devto", "lobsters", "lemmy")
# A name shorter than this is too generic to prove attribution on its own
# ("acme", "data"), so only the full domain counts for those.
_ATTRIBUTION_MIN_NAME = 6
# A page is a *practice* page only if it says something about doing the work.
# Without this gate every blog post on the internet is a "candidate partner",
# because a page is always trivially attributed to its own host. The list is
# data, not code: edit evidence_rules.practice_signals in the plan.
_DEFAULT_PRACTICE_SIGNALS = (
    "case study", "client", "customer", "consulting", "implementation",
    "integration", "migration", "managed service", "professional services",
    "delivery", "practice", "partner", "systems integrator", "hiring",
    "solutions architect", "services",
)


class SourcingError(RuntimeError):
    """The plan is unusable, or a step cannot be attempted at all."""


# Hosts that *talk about* partners rather than being partners: directories,
# registries, community platforms and job boards. Their pages are evidence for
# a partner; they are never candidates themselves.
_SOURCE_HOSTS = REGISTRY_DOMAINS + REVIEW_DOMAINS + COMMUNITY_DOMAINS + ATS_DOMAINS
_SLUG_STOPWORDS = {"case-study", "case-studies", "customers", "clients", "work", "portfolio", "success-stories"}
_LINKED_DOMAIN_RE = re.compile(r'https?://([a-z0-9][a-z0-9.\-]{2,80}?)(?=[/\s"\'<>)\]]|$)', re.IGNORECASE)
# Only these suffixes are treated as a firm's own site when linked from a
# community or directory page; a link to a blog post is not a partner.
_ENTITY_SUFFIXES = (
    ".com", ".io", ".ai", ".dev", ".net", ".co", ".org", ".cloud", ".tech",
    ".sh", ".app", ".us", ".uk", ".de", ".ca", ".au", ".nl", ".se", ".fr",
)


def _host(url: str | None) -> str:
    parsed = urlparse((url or "").strip() if "://" in (url or "") else f"https://{(url or '').strip()}")
    host = parsed.netloc.lower().strip()
    return host[4:] if host.startswith("www.") else host


def is_source_host(host: str) -> bool:
    return any(marker in host for marker in _SOURCE_HOSTS)


def linked_domains(text: str | None) -> list[str]:
    """Firm domains linked from a page, in order, source hosts excluded."""
    out: list[str] = []
    for match in _LINKED_DOMAIN_RE.finditer(text or ""):
        domain = match.group(1).lower().strip(".")
        if domain.startswith("www."):
            domain = domain[4:]
        if "." not in domain or is_source_host(domain):
            continue
        if not domain.endswith(_ENTITY_SUFFIXES):
            continue
        out.append(domain)
    return list(dict.fromkeys(out))


def candidate_entities(url: str | None, text: str | None = None) -> list[str]:
    """Entities a page could be filed under.

    The page's own domain normally identifies the partner. Two exceptions are
    worth catching: a vendor case study (``appomni.com/case-studies/trace3/`` is
    *about* trace3, so the slug is a candidate too), and a page hosted on a
    community or directory site, which files under the firms it links to.
    Attribution then decides which of those the page is really about.
    """
    host = _host(url)
    out: list[str] = []
    if host and is_source_host(host):
        out.extend(linked_domains(text))
        return list(dict.fromkeys(out))
    if host:
        out.append(host)
    match = CASE_STUDY_PATH_RE.search(urlparse((url or "") if "://" in (url or "") else f"https://{url or ''}").path or "")
    if match and host and not is_source_host(host):
        segments = [seg for seg in urlparse((url or "") if "://" in (url or "") else f"https://{url or ''}").path.split("/") if seg]
        if segments:
            slug = segments[-1].lower().strip()
            if (3 <= len(slug) <= 30 and slug not in _SLUG_STOPWORDS
                    and not any(ch.isdigit() and len(slug) == 4 for ch in [slug[:1]])):
                out.append(slug if "." in slug else f"{slug}.com")
    return list(dict.fromkeys(out))


def load_plan(path: str | Path | None = None) -> dict[str, Any]:
    plan_path = Path(path).expanduser() if path else PLAN_PATH
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SourcingError(f"could not read the partner source plan at {plan_path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise SourcingError(f"partner source plan is not valid JSON: {exc}") from exc
    if not isinstance(plan.get("stages"), dict):
        raise SourcingError(f"partner source plan at {plan_path} has no stages")
    return plan


# ---------------------------------------------------------------------------
# Attribution
# ---------------------------------------------------------------------------

def attribution_terms(entity: str) -> tuple[str, ...]:
    """Terms that prove a page is about this partner, strongest first."""
    raw = str(entity or "").strip()
    if not raw:
        return ()
    canonical = (canonicalize_entity_id(raw) or raw).strip().lower()
    if not canonical:
        return ()
    terms = [canonical]
    label = canonical.split(".")[0]
    if len(label) >= _ATTRIBUTION_MIN_NAME and label != canonical:
        terms.append(label)
    return tuple(dict.fromkeys(terms))


def is_attributed(text: str | None, uri: str | None, entity: str) -> bool:
    """True when this page is about `entity`, not merely matched by keywords."""
    uri_l = (uri or "").lower()
    text_l = (text or "").lower()
    for term in attribution_terms(entity):
        if term in uri_l:
            return True
        if any(ch.isdigit() for ch in term):
            # "trace3" is that partner's name and does not appear by accident —
            # but it must be the whole word, so "trace33" is a different firm.
            if re.search(rf"(?<![\w-]){re.escape(term)}(?![\w-])", text_l):
                return True
        elif f" {term} " in f" {text_l} ":
            # A bare word must stand alone: "trace" must not match "tracing".
            return True
    return False


def practice_signals(plan: dict[str, Any] | None = None) -> tuple[str, ...]:
    """Terms that mark a page as being about *delivering* work, from the plan."""
    rules = (plan or {}).get("evidence_rules") or {}
    configured = rules.get("practice_signals")
    if isinstance(configured, list):
        terms = tuple(str(term).strip().lower() for term in configured if str(term).strip())
        if terms:
            return terms
    return _DEFAULT_PRACTICE_SIGNALS


def has_practice_signal(text: str | None, signals: Sequence[str] | None = None) -> bool:
    """True when the page talks about delivering work for clients at all."""
    blob = (text or "").lower()
    return any(term in blob for term in (signals or _DEFAULT_PRACTICE_SIGNALS))


def filter_attributed(
    records: Iterable[RawRecord], entity: str
) -> tuple[list[RawRecord], list[RawRecord]]:
    """Split records into (about this partner, everything else)."""
    kept: list[RawRecord] = []
    dropped: list[RawRecord] = []
    for record in records:
        target = kept if is_attributed(record.text, record.source_uri, entity) else dropped
        target.append(record)
    return kept, dropped


# ---------------------------------------------------------------------------
# Plan expansion
# ---------------------------------------------------------------------------

def _substitute(template: str, values: dict[str, str]) -> str | None:
    """Fill placeholders; None when a required value is missing."""
    out = template
    for key, value in values.items():
        out = out.replace("{" + key + "}", value)
    return None if "{" in out else out


def find_queries(plan: dict[str, Any], *, tech: str = "", vertical: str = "") -> dict[str, list[str]]:
    """Backend -> queries for the cold-start stage, placeholders resolved."""
    stage = plan.get("stages", {}).get("find", {})
    values = {"tech": tech, "vertical": vertical}
    out: dict[str, list[str]] = {}
    for backend, spec in stage.items():
        if backend in ("comment", "fetch"):
            continue
        queries: list[str] = []
        if isinstance(spec, list):
            candidates = spec
        elif isinstance(spec, dict):
            candidates = list(spec.get("queries") or [])
        else:
            continue
        for template in candidates:
            if not tech and "{tech}" in template:
                continue
            if not vertical and "{vertical}" in template:
                continue
            resolved = _substitute(template, values)
            if resolved:
                queries.append(resolved)
        if queries:
            out[backend] = queries
    return out


def enrich_urls(plan: dict[str, Any], entity: str) -> dict[str, list[str]]:
    """Step -> URLs to fetch for one partner (first-party, ATS, third-party)."""
    stage = plan.get("stages", {}).get("enrich", {})
    domain = canonicalize_entity_id(entity) or entity
    slug = domain.split(".")[0]
    origin = f"https://{domain}"
    values = {"domain": domain, "slug": slug, "origin": origin}
    urls: dict[str, list[str]] = {"ats": [], "third_party": []}
    for key in ("ats", "third_party"):
        for template in (stage.get(key) or {}).get("probe") or (stage.get(key) or {}).get("urls") or []:
            resolved = _substitute(template, values)
            if resolved:
                urls[key].append(resolved)
    urls["first_party"] = [_substitute(t, values) or origin for t in (stage.get("first_party") or {}).get("crawl", [])]
    urls["first_party"] = [u if u.startswith("http") else origin + u for u in urls["first_party"]]
    return urls


# ---------------------------------------------------------------------------
# Stages
# ---------------------------------------------------------------------------

@dataclass
class SourcingReport:
    """What happened, so a run can explain itself instead of silently thinning."""

    stage: str
    searched: int = 0
    fetched: int = 0
    kept: int = 0
    dropped_unattributed: int = 0
    dropped_no_practice_signal: int = 0
    skipped: list[dict[str, str]] = field(default_factory=list)
    candidates: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "searched": self.searched,
            "fetched": self.fetched,
            "kept": self.kept,
            "dropped_unattributed": self.dropped_unattributed,
            "dropped_no_practice_signal": self.dropped_no_practice_signal,
            "candidates": self.candidates,
            "skipped": self.skipped,
        }


def _fetch_hits(hits: Sequence[SearchHit], *, timeout: float, respect_robots: bool, snippets_only: bool,
                report: SourcingReport, seen: set[str] | None = None) -> list[RawRecord]:
    """Fetch each URL once, however many queries and backends returned it."""
    records: list[RawRecord] = []
    seen = seen if seen is not None else set()
    for hit in hits:
        if hit.url in seen:
            continue
        seen.add(hit.url)
        if snippets_only:
            records.append(RawRecord(
                text=hit.snippet, source_uri=hit.url, title=hit.title,
                item_id=hit.url, metadata={"evidence": "indicator", "backend": hit.backend},
            ))
            continue
        try:
            records.append(fetch_text(hit.url, timeout=timeout, respect_robots=respect_robots))
        except Exception as exc:  # a dead link must not stop the sourcing run
            report.skipped.append({"url": hit.url, "reason": str(exc)[:200]})
    report.fetched += len(records)
    return records


def find_partners(
    *,
    plan: dict[str, Any] | None = None,
    tech: str = "",
    vertical: str = "",
    backends: Sequence[str] | None = None,
    max_per_query: int = 10,
    searxng_url: str | None = None,
    discourse_url: str | None = None,
    subreddits: Sequence[str] = (),
    se_tagged: Sequence[str] = (),
    se_site: str = "stackoverflow",
    lemmy_instance: str | None = None,
    timeout: float = 20.0,
    delay: float = 1.0,
    respect_robots: bool = True,
    snippets_only: bool = False,
) -> tuple[list[InputItem], SourcingReport]:
    """Cold start: search broadly, fetch what looks promising, bundle per entity."""
    plan = plan or load_plan()
    report = SourcingReport(stage="find")
    queries = find_queries(plan, tech=tech, vertical=vertical)
    if backends:
        queries = {b: q for b, q in queries.items() if b in set(backends)}
    if not queries:
        raise SourcingError("no searchable queries in the plan for this tech/vertical; nothing to run")

    records: list[RawRecord] = []
    seen_urls: set[str] = set()
    for backend, backend_queries in queries.items():
        for query in backend_queries:
            report.searched += 1
            try:
                hits = web_search(
                    query,
                    backends=[backend],
                    max_results=max_per_query,
                    searxng_url=searxng_url,
                    timeout=timeout,
                    reddit_subreddits=subreddits,
                    se_tagged=se_tagged,
                    se_site=se_site,
                    discourse_url=discourse_url,
                    lemmy_instance=lemmy_instance or "https://programming.dev",
                )
            except Exception as exc:
                report.skipped.append({"backend": backend, "query": query, "reason": str(exc)[:200]})
                continue
            records.extend(_fetch_hits(
                hits, timeout=timeout, respect_robots=respect_robots,
                snippets_only=snippets_only, report=report, seen=seen_urls,
            ))

    # File each hit under the entity it is actually about. A page that names
    # nobody it could be filed under is a lead, not evidence; so is a page that
    # never mentions doing the work (a vendor blog, a news article, a thread).
    signals = practice_signals(plan)
    filed: list[InputItem] = []
    for item in to_input_items(records):
        if not has_practice_signal(item.text, signals):
            report.dropped_no_practice_signal += 1
            continue
        placed = False
        for entity in candidate_entities(item.source_uri, item.text):
            if is_attributed(item.text, item.source_uri, entity):
                filed.append(item.model_copy(update={"item_id": entity}))
                placed = True
        if not placed:
            report.dropped_unattributed += 1
    report.candidates = sorted({item.item_id for item in filed})

    items = bundle_records(filed)
    report.kept = len(items)
    return items, report


def enrich_partner(
    entity: str,
    *,
    plan: dict[str, Any] | None = None,
    backends: Sequence[str] | None = None,
    max_pages: int = 8,
    max_per_query: int = 8,
    searxng_url: str | None = None,
    timeout: float = 20.0,
    delay: float = 1.0,
    respect_robots: bool = True,
    snippets_only: bool = False,
    include_fetch: bool = True,
) -> tuple[list[InputItem], SourcingReport]:
    """Enrich one partner (from find, or from a list you already have)."""
    plan = plan or load_plan()
    report = SourcingReport(stage="enrich", candidates=[entity])
    domain = canonicalize_entity_id(entity) or entity
    stage = plan.get("stages", {}).get("enrich", {})
    records: list[RawRecord] = []
    seen_urls: set[str] = set()

    if include_fetch:
        urls = enrich_urls(plan, domain)
        # First-party: crawl the site shallowly and keep the pages the plan
        # cares about (services, partners, case studies, careers).
        try:
            crawled, skipped = crawl_site(
                f"https://{domain}", max_pages=max_pages, max_depth=2, timeout=timeout,
                delay=delay, respect_robots=respect_robots,
            )
            hints = tuple((stage.get("first_party") or {}).get("crawl") or ())
            keep = [r for r in crawled if not hints or any(h in r.source_uri.lower() for h in hints)]
            records.extend(keep or crawled)
            report.skipped.extend({"url": s.get("url", ""), "reason": s.get("reason", "")} for s in skipped[:5])
        except Exception as exc:
            report.skipped.append({"url": f"https://{domain}", "reason": str(exc)[:200]})

        for kind in ("ats", "third_party"):
            for url in urls.get(kind, []):
                try:
                    records.append(fetch_text(url, timeout=timeout, respect_robots=respect_robots))
                except Exception as exc:
                    report.skipped.append({"url": url, "reason": str(exc)[:200]})

    # Independent mentions and press, via the search backends. --no-fetch means
    # no fetching at all, so search hits stay snippets in that mode.
    snippets_only = snippets_only or not include_fetch
    search_backends = list(backends) if backends else [*COMMUNITY_BACKENDS, "ddgs"]
    queries = [f'"{domain}"'] + [
        _substitute(q, {"domain": domain}) or ""
        for q in (stage.get("web") or {}).get("queries", [])
    ]
    for query in [q for q in queries if q]:
        for backend in search_backends:
            report.searched += 1
            try:
                hits = web_search(
                    query, backends=[backend], max_results=max_per_query,
                    searxng_url=searxng_url, timeout=timeout,
                )
            except Exception as exc:
                report.skipped.append({"backend": backend, "query": query, "reason": str(exc)[:200]})
                continue
            records.extend(_fetch_hits(
                hits, timeout=timeout, respect_robots=respect_robots,
                snippets_only=snippets_only, report=report, seen=seen_urls,
            ))

    attributed, dropped = filter_attributed(records, domain)
    report.dropped_unattributed = len(dropped)
    # One dossier per partner: re-key every page to the entity so the bundle
    # merges into a single row instead of one row per URL.
    keyed = [item.model_copy(update={"item_id": domain}) for item in to_input_items(attributed)]
    items = bundle_records(keyed)
    report.kept = len(items)
    return items, report
