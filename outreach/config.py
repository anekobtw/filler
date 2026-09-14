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
    field_signals = [
        value
        for keyword in association_keywords
        if (value := config_value(config, keyword))
    ]
    configured_signals = config.get("associationSignals", [])
    if not isinstance(configured_signals, list) or not all(
        isinstance(signal, str) for signal in configured_signals
    ):
        raise ValueError("associationSignals must be a list of strings")
    return linkedin, list(dict.fromkeys([*field_signals, *configured_signals]))[:10]


def sender_email(config_path: Path) -> str:
    return config_value(load_config(config_path), "email")
