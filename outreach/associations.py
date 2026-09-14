import csv
import re
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .config import applicant_details
from .firefox import search_firefox

DEFAULT_CONFIG = Path.cwd() / "resume.config.json"
PROFILE_USER_AGENT = "Mozilla/5.0 (compatible; assoc/0.1)"
ACRONYM_STOP_WORDS = frozenset({"and", "at", "of", "the"})



@dataclass(frozen=True)
class SearchResult:
    name: str
    url: str
    snippet: str


class _ProfileTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def normalized_text(value: str) -> str:
    return " ".join(unescape(value).casefold().split())


def association_terms(signal: str) -> set[str]:
    terms = {normalized_text(signal)}
    words = re.findall(r"[a-z0-9]+", signal.casefold())
    acronym = "".join(word[0] for word in words if word not in ACRONYM_STOP_WORDS)
    if len(acronym) >= 3:
        terms.add(acronym)
    return terms


def association_matches(row: dict[str, str], associations: list[str]) -> list[str]:
    row_text = normalized_text(" ".join(value or "" for value in row.values()))
    return [
        signal
        for signal in associations
        if any(term in row_text for term in association_terms(signal) if term)
    ]


def is_linkedin_profile(url: str) -> bool:
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").casefold()
    return (
        parsed.scheme in {"http", "https"}
        and (hostname == "linkedin.com" or hostname.endswith(".linkedin.com"))
        and parsed.path.startswith("/in/")
    )


def fetch_linkedin_profile(url: str) -> str:
    if not is_linkedin_profile(url):
        return ""
    request = Request(url, headers={"User-Agent": PROFILE_USER_AGENT})
    with urlopen(request, timeout=10) as response:
        parser = _ProfileTextExtractor()
        parser.feed(response.read().decode("utf-8", errors="replace"))
    return normalized_text(" ".join(parser.parts))


def linkedin_candidates(
    company: str, associations: list[str]
) -> list[tuple[SearchResult, list[str]]]:
    """Search through the extension in the user's existing Firefox session."""
    queries = [{"keywords": company, "direct": True}]
    if associations:
        shared = " OR ".join(f'"{signal.replace(chr(34), "")}"' for signal in associations)
        queries.append({"keywords": f'"{company.replace(chr(34), "")}" AND ({shared})', "direct": False})
    candidates: dict[str, tuple[SearchResult, list[str]]] = {}
    for row in search_firefox(queries):
        matches = association_matches({"text": row["snippet"]}, associations)
        if row["direct"]:
            matches.insert(0, "1st-degree connection (LinkedIn search)")
        elif not matches:
            matches = ["Shared-association search result; verify profile"]
        candidates.setdefault(
            row["url"], (SearchResult(row["name"], row["url"], row["snippet"]), matches)
        )
    return list(candidates.values())



def connection_candidates(
    path: Path,
    company: str,
    associations: list[str],
    profile_fetcher: Callable[[str], str] = fetch_linkedin_profile,
) -> list[tuple[SearchResult, list[str]]]:
    company_term = normalized_text(company)
    candidates: list[tuple[SearchResult, list[str]]] = []
    with path.open(encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            company_match = company_term in normalized_text(row.get("Company") or "")
            matches = association_matches(row, associations)
            if not company_match and not matches:
                continue

            name = " ".join(
                part
                for part in (row.get("First Name", ""), row.get("Last Name", ""))
                if part
            ).strip() or row.get("Name", "Unknown connection")
            url = row.get("Profile URL") or row.get("LinkedIn URL") or ""
            if url:
                try:
                    profile_text = profile_fetcher(url)
                except OSError:
                    profile_text = ""
                if company_term in normalized_text(profile_text):
                    matches.append(f"LinkedIn profile: {company}")
            if company_match:
                matches.insert(0, f"LinkedIn connection: {company}")
            candidates.append(
                (
                    SearchResult(
                        name=name,
                        url=url,
                        snippet=" at ".join(
                            part
                            for part in (row.get("Position", ""), row.get("Company", ""))
                            if part
                        ),
                    ),
                    matches,
                )
            )
    return sorted(candidates, key=lambda item: item[0].name.casefold())


def find_candidates(
    company: str, connections_path: Path | None, associations: list[str]
) -> list[tuple[SearchResult, list[str]]]:
    if connections_path is None:
        return linkedin_candidates(company, associations)
    return connection_candidates(connections_path, company, associations)


def main() -> None:
    company = input("Company to search: ").strip()
    if not company:
        raise SystemExit("A company name is required.")

    config_linkedin, associations = applicant_details(DEFAULT_CONFIG)
    applicant_linkedin = (
        input(f"Applicant LinkedIn URL [{config_linkedin}]: ").strip()
        or config_linkedin
    )
    connections_value = input(
        "LinkedIn connections CSV export (blank = use your Firefox LinkedIn session): "
    ).strip()
    connections_path = Path(connections_value) if connections_value else None

    try:
        candidates = find_candidates(company, connections_path, associations)
    except (OSError, RuntimeError) as error:
        raise SystemExit(str(error)) from error
    except KeyboardInterrupt:
        raise SystemExit("Search cancelled.") from None
    print(f"Applicant: {applicant_linkedin}")
    print(f"Company: {company}")
    print(
        "Association signals: "
        + (", ".join(associations) if associations else "none in config")
    )
    print()
    if not candidates:
        source = "CSV export" if connections_path else "LinkedIn people search (first three pages per query)"
        print(f"No matches returned by {source}.")
        return
    for index, (candidate, matches) in enumerate(candidates[:20], start=1):
        signal = ", ".join(matches) if matches else "company match only"
        profile = candidate.url or "Profile URL unavailable in export"
        print(f"{index}. {candidate.name}\n   {profile}\n   Association: {signal}")
        if candidate.snippet:
            print(f"   {candidate.snippet}")


if __name__ == "__main__":
    main()
