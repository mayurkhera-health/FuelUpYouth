"""Approved nutrition coach source organizations — answers are grounded only in these."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse


@dataclass(frozen=True)
class ApprovedSource:
    id: str
    name: str
    url: str
    keywords: tuple[str, ...]
    domains: tuple[str, ...]


APPROVED_SOURCES: tuple[ApprovedSource, ...] = (
    ApprovedSource(
        id="acsm",
        name="American College of Sports Medicine",
        url="https://www.acsm.org",
        keywords=("acsm", "american college of sports medicine"),
        domains=("acsm.org", "journals.lww.com"),
    ),
    ApprovedSource(
        id="and",
        name="Academy of Nutrition and Dietetics",
        url="https://www.eatright.org",
        keywords=("academy of nutrition and dietetics", "eatright", "registered dietitian"),
        domains=("eatright.org", "eatrightpro.org"),
    ),
    ApprovedSource(
        id="gssi",
        name="Gatorade Sports Science Institute",
        url="https://www.gssiweb.org",
        keywords=("gatorade sports science", "gssi"),
        domains=("gssiweb.org",),
    ),
    ApprovedSource(
        id="issn",
        name="International Society of Sports Nutrition",
        url="https://www.sportsnutritionsociety.org",
        keywords=("international society of sports nutrition", "issn", "jissn"),
        domains=("sportsnutritionsociety.org", "jissn.biomedcentral.com"),
    ),
    ApprovedSource(
        id="aap",
        name="American Academy of Pediatrics",
        url="https://www.aap.org",
        keywords=("american academy of pediatrics", "aap"),
        domains=("aap.org", "publications.aap.org"),
    ),
    ApprovedSource(
        id="usopc",
        name="United States Olympic & Paralympic Committee",
        url="https://www.teamusa.org",
        keywords=("united states olympic", "usopc", "team usa", "paralympic committee"),
        domains=("teamusa.org", "usopc.org"),
    ),
    ApprovedSource(
        id="ncaa_ssi",
        name="NCAA Sport Science Institute",
        url="https://www.ncaa.org/sport-science-institute",
        keywords=("ncaa sport science", "ncaa sport science institute"),
        domains=("ncaa.org",),
    ),
    ApprovedSource(
        id="amssm",
        name="American Medical Society for Sports Medicine",
        url="https://www.amssm.org",
        keywords=("american medical society for sports medicine", "amssm"),
        domains=("amssm.org",),
    ),
    ApprovedSource(
        id="cps",
        name="Canadian Paediatric Society",
        url="https://cps.ca",
        keywords=("canadian paediatric society", "canadian pediatric society", "cps"),
        domains=("cps.ca",),
    ),
    ApprovedSource(
        id="ksi",
        name="Korey Stringer Institute",
        url="https://koreystringerinstitute.uconn.edu",
        keywords=("korey stringer institute", "ksi"),
        domains=("koreystringerinstitute.uconn.edu", "uconn.edu"),
    ),
)

_APPROVED_IDS = {s.id for s in APPROVED_SOURCES}


def list_sources() -> list[dict]:
    return [{"id": s.id, "name": s.name, "url": s.url} for s in APPROVED_SOURCES]


def approved_domains() -> list[str]:
    """Unique hostnames allowed for live web search."""
    seen: set[str] = set()
    domains: list[str] = []
    for source in APPROVED_SOURCES:
        for domain in source.domains:
            if domain not in seen:
                seen.add(domain)
                domains.append(domain)
    return domains


def match_approved_source(url: str) -> Optional[ApprovedSource]:
    """Return the approved org for a URL host, if any."""
    host = urlparse(url).netloc.lower().removeprefix("www.")
    if not host:
        return None
    for org in APPROVED_SOURCES:
        if any(host == d or host.endswith("." + d) for d in org.domains):
            return org
    return None


def is_approved_org_id(org_id: str | None) -> bool:
    return bool(org_id and org_id in _APPROVED_IDS)


def resolve_organization(
    source: str | None,
    source_urls: list | None,
    organization_id: str | None = None,
) -> Optional[ApprovedSource]:
    """Match a knowledge item to one approved organization."""
    if organization_id:
        for org in APPROVED_SOURCES:
            if org.id == organization_id:
                return org

    text = (source or "").lower()
    for org in APPROVED_SOURCES:
        if any(kw in text for kw in org.keywords):
            return org

    for raw_url in source_urls or []:
        if not raw_url:
            continue
        host = urlparse(raw_url).netloc.lower().removeprefix("www.")
        for org in APPROVED_SOURCES:
            if any(host == d or host.endswith("." + d) for d in org.domains):
                return org

    return None
