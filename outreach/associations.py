import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus, urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from .config import applicant_details

DEFAULT_CONFIG = Path.cwd() / "resume.config.json"
SEARCH_URL = "https://www.bing.com/search?format=rss&q={query}"
USER_AGENT = "Mozilla/5.0 (compatible; ResumeFillerAssociationFinder/0.1)"


@dataclass(frozen=True)
class SearchResult:
    name: str
    url: str
    snippet: str


def linkedin_profile_url(url: str) -> str | None:
    parsed = urlparse(url)
    host = parsed.netloc.removeprefix("www.").lower()
    if host == "linkedin.com" and parsed.path.startswith("/in/"):
        return url
    return None


def plain_text(value: str) -> str:
    return " ".join(re.sub(r"<[^>]+>", " ", value).split())


def search(query: str) -> list[SearchResult]:
    request = Request(
        SEARCH_URL.format(query=quote_plus(query)),
        headers={"User-Agent": USER_AGENT},
    )
    try:
        with urlopen(request, timeout=15) as response:
            document = response.read()
    except (HTTPError, URLError) as error:
        print(f"warning: search failed for {query!r}: {error}", file=sys.stderr)
        return []

    try:
        root = ElementTree.fromstring(document)
    except ElementTree.ParseError as error:
        print(
            f"warning: invalid search response for {query!r}: {error}", file=sys.stderr
        )
        return []
    return [
        SearchResult(
            name=plain_text(item.findtext("title", default="")),
            url=item.findtext("link", default=""),
            snippet=plain_text(item.findtext("description", default="")),
        )
        for item in root.findall("./channel/item")
    ]


def candidate_score(
    result: SearchResult, associations: list[str]
) -> tuple[int, list[str]]:
    searchable = f"{result.name} {result.snippet}".casefold()
    matches = [term for term in associations if term.casefold() in searchable]
    return len(matches), matches


def find_candidates(
    company: str, applicant_linkedin: str, associations: list[str]
) -> list[tuple[SearchResult, list[str]]]:
    queries = [f'site:linkedin.com/in/ "{company}"']
    queries.extend(
        f'site:linkedin.com/in/ "{company}" "{term}"' for term in associations
    )
    candidates: dict[str, SearchResult] = {}
    for query in queries:
        for result in search(query):
            url = linkedin_profile_url(result.url)
            if url and url.rstrip("/") != applicant_linkedin.rstrip("/"):
                candidates.setdefault(
                    url, SearchResult(result.name, url, result.snippet)
                )

    scored = [
        (result, candidate_score(result, associations)[1])
        for result in candidates.values()
    ]
    return sorted(scored, key=lambda item: (-len(item[1]), item[0].name.casefold()))


def main() -> None:
    company = input("Company to search: ").strip()
    if not company:
        raise SystemExit("A company name is required.")

    config_linkedin, associations = applicant_details(DEFAULT_CONFIG)
    applicant_linkedin = (
        input(f"Applicant LinkedIn URL [{config_linkedin}]: ").strip()
        or config_linkedin
    )

    candidates = find_candidates(company, applicant_linkedin, associations)
    print(f"Applicant: {applicant_linkedin}")
    print(f"Company: {company}")
    print(
        "Association signals: "
        + (", ".join(associations) if associations else "none in config")
    )
    print()
    if not candidates:
        print("No publicly indexed LinkedIn profiles found.")
        return
    for index, (candidate, matches) in enumerate(candidates[:20], start=1):
        signal = ", ".join(matches) if matches else "company match only"
        print(
            f"{index}. {candidate.name}\n   {candidate.url}\n   Association: {signal}"
        )
        if candidate.snippet:
            print(f"   {candidate.snippet}")


if __name__ == "__main__":
    main()
