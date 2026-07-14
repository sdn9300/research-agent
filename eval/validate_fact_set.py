from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import urlparse


FACT_SET_PATH = Path("eval/fact_set.json")
MIN_COMPANY_COUNT = 15
MIN_FACTS_PER_COMPANY = 3
MAX_FACTS_PER_COMPANY = 5
ALLOWED_STATUSES = {"FROZEN", "FROZEN_VERIFIED"}
ALLOWED_SOURCE_CLASSES = {"official", "secondary"}
REQUIRED_TOP_LEVEL_FIELDS = {
    "dataset_id",
    "status",
    "frozen_on",
    "frozen_by",
    "governing_document",
    "companies",
}
REQUIRED_COMPANY_FIELDS = {"company_name", "coverage_tier", "facts"}
REQUIRED_FACT_FIELDS = {"fact_id", "category", "claim", "verification_url", "source_class"}


def _is_non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_valid_http_url(value: object) -> bool:
    if not _is_non_empty_string(value):
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def validate_fact_set(path: Path) -> list[str]:
    errors: list[str] = []

    if not path.exists():
        return [f"Fact set not found: {path}"]

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"Invalid JSON: {exc}"]

    for field in sorted(REQUIRED_TOP_LEVEL_FIELDS):
        if field not in data:
            errors.append(f"Missing top-level field: {field}")

    status = data.get("status")
    if status not in ALLOWED_STATUSES:
        errors.append(
            f"Invalid status: {status!r}. Expected one of {sorted(ALLOWED_STATUSES)}."
        )

    companies = data.get("companies")
    if not isinstance(companies, list):
        errors.append("Top-level 'companies' must be a list.")
        return errors

    if len(companies) < MIN_COMPANY_COUNT:
        errors.append(
            f"Company count too low: found {len(companies)}, expected at least {MIN_COMPANY_COUNT}."
        )

    seen_company_names: set[str] = set()
    seen_fact_ids: set[str] = set()

    for company_index, company in enumerate(companies, start=1):
        prefix = f"Company #{company_index}"

        if not isinstance(company, dict):
            errors.append(f"{prefix} must be an object.")
            continue

        for field in sorted(REQUIRED_COMPANY_FIELDS):
            if field not in company:
                errors.append(f"{prefix} missing field: {field}")

        company_name = company.get("company_name")
        if not _is_non_empty_string(company_name):
            errors.append(f"{prefix} has invalid company_name.")
            continue

        if company_name in seen_company_names:
            errors.append(f"Duplicate company_name: {company_name}")
        seen_company_names.add(company_name)

        facts = company.get("facts")
        if not isinstance(facts, list):
            errors.append(f"{company_name}: 'facts' must be a list.")
            continue

        if not (MIN_FACTS_PER_COMPANY <= len(facts) <= MAX_FACTS_PER_COMPANY):
            errors.append(
                f"{company_name}: fact count is {len(facts)}; expected between "
                f"{MIN_FACTS_PER_COMPANY} and {MAX_FACTS_PER_COMPANY}."
            )

        for fact_index, fact in enumerate(facts, start=1):
            fact_prefix = f"{company_name} fact #{fact_index}"

            if not isinstance(fact, dict):
                errors.append(f"{fact_prefix} must be an object.")
                continue

            for field in sorted(REQUIRED_FACT_FIELDS):
                if field not in fact:
                    errors.append(f"{fact_prefix} missing field: {field}")

            fact_id = fact.get("fact_id")
            if not _is_non_empty_string(fact_id):
                errors.append(f"{fact_prefix} has invalid fact_id.")
            elif fact_id in seen_fact_ids:
                errors.append(f"Duplicate fact_id detected: {fact_id}")
            else:
                seen_fact_ids.add(fact_id)

            if not _is_non_empty_string(fact.get("category")):
                errors.append(f"{fact_prefix} has invalid category.")

            if not _is_non_empty_string(fact.get("claim")):
                errors.append(f"{fact_prefix} has invalid claim.")

            verification_url = fact.get("verification_url")
            if not _is_valid_http_url(verification_url):
                errors.append(f"{fact_prefix} has invalid verification_url: {verification_url!r}")

            source_class = fact.get("source_class")
            if source_class not in ALLOWED_SOURCE_CLASSES:
                errors.append(
                    f"{fact_prefix} has invalid source_class: {source_class!r}. "
                    f"Expected one of {sorted(ALLOWED_SOURCE_CLASSES)}."
                )

    return errors


def main() -> int:
    errors = validate_fact_set(FACT_SET_PATH)
    if errors:
        print("Gate 1 fact-set validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Gate 1 fact-set validation passed.")
    print(f"Validated file: {FACT_SET_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
