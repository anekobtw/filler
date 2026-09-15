import re
from dataclasses import dataclass
from html import unescape
from pathlib import Path

from .config import applicant_details
from .firefox import search_firefox

DEFAULT_CONFIG = Path.cwd() / "resume.config.json"
ACRONYM_STOP_WORDS = frozenset({"and", "at", "of", "the"})



@dataclass(frozen=True)
class SearchResult:
    name: str
    url: str
    snippet: str

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





def linkedin_candidates(
    company: str, associations: list[str], show_progress: bool = True
) -> list[tuple[SearchResult, list[str]]]:
    """Search through the extension in the user's existing Firefox session."""
    queries = [{"keywords": company, "direct": True}]
    if associations:
        shared = " OR ".join(f'"{signal.replace(chr(34), "")}"' for signal in associations)
        queries.append({"keywords": f'"{company.replace(chr(34), "")}" AND ({shared})', "direct": False})
    candidates: dict[str, tuple[SearchResult, list[str]]] = {}
    for row in search_firefox(queries, show_progress=show_progress):
        matches = association_matches({"text": row["snippet"]}, associations)
        if row["direct"]:
            matches.insert(0, "1st-degree connection (LinkedIn search)")
        elif not matches:
            matches = ["Shared-association search result; verify profile"]
        candidates.setdefault(
            row["url"], (SearchResult(row["name"], row["url"], row["snippet"]), matches)
        )
    return list(candidates.values())




def main() -> None:
    company = input("Company to search: ").strip()
    if not company:
        raise SystemExit("A company name is required.")

    config_linkedin, associations = applicant_details(DEFAULT_CONFIG)
    applicant_linkedin = (
        input(f"Applicant LinkedIn URL [{config_linkedin}]: ").strip()
        or config_linkedin
    )
    try:
        candidates = linkedin_candidates(company, associations)
    except RuntimeError as error:
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
        print("No matches returned by LinkedIn people search (first three pages per query).")
        return
    for index, (candidate, matches) in enumerate(candidates[:20], start=1):
        signal = ", ".join(matches) if matches else "company match only"
        profile = candidate.url
        print(f"{index}. {candidate.name}\n   {profile}\n   Association: {signal}")
        if candidate.snippet:
            print(f"   {candidate.snippet}")


if __name__ == "__main__":
    main()
