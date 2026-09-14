import json
from pathlib import Path


def config_value(config: dict[str, object], keyword: str) -> str:
    for field in config["fields"]:
        if keyword in field["keywords"]:
            return field["value"].strip()
    return ""


def load_config(config_path: Path) -> dict[str, object]:
    return json.loads(config_path.read_text(encoding="utf-8"))


def applicant_details(config_path: Path) -> tuple[str, list[str]]:
    config = load_config(config_path)
    linkedin = config_value(config, "linkedin")
    association_keywords = (
        "school", "university", "college", "institution", "location", "city",
        "company", "employer", "organization",
    )
    associations = [
        value
        for keyword in association_keywords
        if (value := config_value(config, keyword))
    ]
    return linkedin, list(dict.fromkeys(associations))[:5]


def sender_email(config_path: Path) -> str:
    return config_value(load_config(config_path), "email")
