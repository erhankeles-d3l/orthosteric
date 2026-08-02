"""CrossRef connector for DOI resolution and publication metadata.

Objective: SCI0-006b.
CrossRef provides DOI metadata (title, authors, journal, year, license).
License is the primary TDM-permission signal: only CC-BY, CC-BY-SA, and
CC0 are treated as TDM-permitted at this layer.

CrossRef does NOT provide full text; it routes to PMC or publisher.
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from orthosteric.data.config import chembl_request_timeout_s

_CROSSREF_BASE = "https://api.crossref.org/works"
_TDM_PERMITTED_LICENSES: frozenset[str] = frozenset(
    {
        "https://creativecommons.org/licenses/by/4.0/",
        "https://creativecommons.org/licenses/by/3.0/",
        "https://creativecommons.org/licenses/by-sa/4.0/",
        "https://creativecommons.org/licenses/by-sa/3.0/",
        "https://creativecommons.org/publicdomain/zero/1.0/",
        "http://creativecommons.org/licenses/by/4.0/",
        "http://creativecommons.org/licenses/by/3.0/",
        "http://creativecommons.org/licenses/by-sa/4.0/",
        "http://creativecommons.org/licenses/by-sa/3.0/",
        "http://creativecommons.org/publicdomain/zero/1.0/",
    }
)


@dataclass
class PublicationMetadata:
    """CrossRef-derived metadata for one publication."""

    doi: str
    title: str | None
    journal: str | None
    year: int | None
    authors: list[str]
    pmid: str | None
    pmcid: str | None
    license_url: str | None
    tdm_permitted: bool
    raw_payload: dict[str, Any]


def _parse_crossref_work(doi: str, work: dict[str, Any]) -> PublicationMetadata:
    title_list = work.get("title", [])
    title = title_list[0] if title_list else None

    container = work.get("container-title", [])
    journal = container[0] if container else None

    date_parts = work.get("published-print", work.get("published-online", {}))
    parts = date_parts.get("date-parts", [[None]])
    year = int(parts[0][0]) if parts and parts[0] and parts[0][0] else None

    authors = []
    for a in work.get("author", []):
        given = a.get("given", "")
        family = a.get("family", "")
        authors.append(f"{given} {family}".strip())

    licenses = work.get("license", [])
    license_url: str | None = None
    tdm_permitted = False
    for lic in licenses:
        url = lic.get("URL", "")
        if url in _TDM_PERMITTED_LICENSES:
            license_url = url
            tdm_permitted = True
            break
        if license_url is None:
            license_url = url

    # CrossRef may carry PubMed/PMC IDs in externalIds
    pmid: str | None = None
    pmcid: str | None = None
    for ext in work.get("link", []):
        url = ext.get("URL", "")
        if "pubmed" in url.lower() and pmid is None:
            pmid = url.rsplit("/", 1)[-1]

    return PublicationMetadata(
        doi=doi,
        title=title,
        journal=journal,
        year=year,
        authors=authors,
        pmid=pmid,
        pmcid=pmcid,
        license_url=license_url,
        tdm_permitted=tdm_permitted,
        raw_payload=work,
    )


class CrossRefConnector:
    """CrossRef REST API connector for publication metadata.

    Used in the SCI0-006b pipeline as the first step: resolve a DOI
    and determine whether TDM is permitted before attempting full-text
    retrieval.
    """

    def __init__(self) -> None:
        self._timeout = chembl_request_timeout_s()
        self._email: str = "orthosteric-data-pipeline@project.internal"

    def version(self) -> str:
        return "crossref-api-v1"

    def metadata(self) -> dict[str, str]:
        return {
            "name": "CrossRef",
            "url": "https://api.crossref.org/",
            "license": "Crossref Metadata Plus (public metadata is openly available)",
        }

    def lookup_doi(self, doi: str) -> PublicationMetadata | None:
        """Fetch metadata for a single DOI from CrossRef.

        Returns None if the DOI cannot be resolved.  Never raises on
        a 404; returns None so callers can handle missing DOIs gracefully.
        """
        encoded = urllib.parse.quote(doi, safe="")
        url = f"{_CROSSREF_BASE}/{encoded}"
        headers = {"User-Agent": f"OrthostericDataPipeline/1.0 mailto:{self._email}"}
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                data: dict[str, Any] = json.loads(resp.read())
            work = data.get("message", {})
            return _parse_crossref_work(doi, work)
        except Exception:
            return None

    def batch_lookup(self, dois: list[str]) -> dict[str, PublicationMetadata | None]:
        """Look up a list of DOIs.  Returns a dict keyed by DOI."""
        results: dict[str, PublicationMetadata | None] = {}
        for doi in dois:
            results[doi] = self.lookup_doi(doi)
            time.sleep(0.1)  # polite rate limiting (CrossRef requests 10 rps max)
        return results

    def search_pi3k(
        self, query: str = "PI3K PIK3CA selectivity inhibitor", max_results: int = 100
    ) -> list[PublicationMetadata]:
        """Search CrossRef for PI3K-relevant publications."""
        params = urllib.parse.urlencode(
            {
                "query": query,
                "rows": min(max_results, 100),
                "mailto": self._email,
                "filter": "has-abstract:true",
            }
        )
        url = f"{_CROSSREF_BASE}?{params}"
        headers = {"User-Agent": f"OrthostericDataPipeline/1.0 mailto:{self._email}"}
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                data: dict[str, Any] = json.loads(resp.read())
        except Exception:
            return []
        items = data.get("message", {}).get("items", [])
        results = []
        for item in items:
            doi = item.get("DOI", "")
            if doi:
                results.append(_parse_crossref_work(doi, item))
        return results
