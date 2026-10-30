"""Full scan with non-identifying aggregates. No row-level data leaves the source."""

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from .arcgis import LAYER, ArcGISClient, ArcGISError

OFFICIAL_RECORDS = (
    "https://assessor.saccounty.gov/us/en/maps-property-data-and-records/assessor-records.html"
)
SINGLE_FAMILY = "Single Family Residence"
FIELDS = (
    "Property_Type",
    "INDICATED_SALES_PRICE",
    "DOCUMENT_DATE",
    "PARCEL_NUMBER",
    "DOCUMENT_PAGE",
    "DOCUMENT_TYPE",
    "BUILDING_SF",
    "LOT_SIZE_SQFEET",
    "NUMBER_OF_BEDROOMS",
    "NUMBER_OF_BATHS",
)


def price(value):
    if value is None or str(value).strip() == "":
        return None
    try:
        number = Decimal(str(value).replace(",", "").replace("$", "").strip())
        return number if number.is_finite() and number > 0 else None
    except InvalidOperation:
        return None


def audit(client=None):
    client = client or ArcGISClient()
    result = {
        "status": "NOT VERIFIED",
        "decision": "NO-GO",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "sources": [LAYER, OFFICIAL_RECORDS],
        "legal_note": "The official assessor records page calls assessor-collected market comparable sales data confidential. Public layer presence does not establish bulk reuse permission or arms-length sale semantics; written clarification required.",
        "counts": None,
        "field_names": None,
        "property_types": None,
        "date_range": None,
        "geography": None,
        "metadata_sha256": None,
        "error": None,
    }
    try:
        metadata = client.metadata()
        result["metadata_sha256"] = hashlib.sha256(
            json.dumps(metadata, sort_keys=True).encode()
        ).hexdigest()
        names = {field["name"] for field in metadata["fields"]}
        result["field_names"] = sorted(names)
        result["pagination_supported"] = metadata.get("advancedQueryCapabilities", {}).get(
            "supportsPagination"
        )
        result["max_record_count"] = metadata.get("maxRecordCount")
        result["geometry_type"] = metadata.get("geometryType")
        result["geography"] = metadata.get("extent")
        result["time_info"] = metadata.get("timeInfo")
        oid = metadata["objectIdField"]
        required = {oid, "Property_Type", "INDICATED_SALES_PRICE", "DOCUMENT_DATE"}
        missing = required - names
        if missing:
            raise ArcGISError(f"Required fields absent: {sorted(missing)}")
        total = client.count()
        fields = [oid, *(field for field in FIELDS if field in names)]
        types, nulls, duplicates, prices = Counter(), Counter(), 0, Counter()
        keys = set()
        earliest = latest = None
        scanned = 0
        for row in client.iter_features(metadata, fields, total):
            scanned += 1
            types[str(row.get("Property_Type"))] += 1
            for field in fields:
                nulls[field] += row.get(field) is None or row.get(field) == ""
            raw = row.get("INDICATED_SALES_PRICE")
            prices[
                "missing"
                if raw is None or str(raw).strip() == ""
                else "positive"
                if price(raw)
                else "nonpositive_or_invalid"
            ] += 1
            date = row.get("DOCUMENT_DATE")
            if isinstance(date, (float, int)):
                earliest = date if earliest is None else min(earliest, date)
                latest = date if latest is None else max(latest, date)
            # Candidate duplicate key only; confirm recording semantics before deduplicating.
            key = (
                row.get("PARCEL_NUMBER"),
                date,
                row.get("DOCUMENT_PAGE"),
                row.get("DOCUMENT_TYPE"),
            )
            if key[0] and key[1]:
                duplicates += key in keys
                keys.add(key)
        result["counts"] = {
            "total_reported": total,
            "scanned": scanned,
            "single_family": types[SINGLE_FAMILY],
            "valid_positive_prices": prices["positive"],
            "missing_price": prices["missing"],
            "invalid_or_nonpositive_price": prices["nonpositive_or_invalid"],
            "candidate_duplicate_transaction_keys": duplicates,
            "missing_by_field": dict(nulls),
        }
        result["property_types"] = dict(types)
        result["date_range"] = {
            "min_utc": datetime.fromtimestamp(earliest / 1000, timezone.utc).isoformat()
            if earliest is not None
            else None,
            "max_utc": datetime.fromtimestamp(latest / 1000, timezone.utc).isoformat()
            if latest is not None
            else None,
        }
        result["status"] = "VERIFIED API COUNTS; SEMANTICS/TERMS UNVERIFIED"
        result["decision"] = (
            "NO-GO"  # Hard gate: positive numbers do not establish market sale or licensed reuse.
        )
    except (ArcGISError, KeyError, TypeError, ValueError) as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def write_report(result, directory):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "data_audit.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    (directory / "data_audit.md").write_text(
        "# Sacramento data audit\n\n"
        f"**Status:** {result['status']}  \n**Decision:** {result['decision']}\n\n"
        f"Checked UTC: {result['checked_at_utc']}\n\n"
        "## Sources\n\n" + "\n".join(f"- {url}" for url in result["sources"]) + "\n\n"
        "## Results\n\n```json\n"
        + json.dumps(
            {
                key: result[key]
                for key in (
                    "counts",
                    "field_names",
                    "property_types",
                    "date_range",
                    "geography",
                    "pagination_supported",
                    "metadata_sha256",
                )
                if key in result
            },
            indent=2,
        )
        + "\n```\n\n"
        f"## Blockers\n\n{result['legal_note']}\n\n"
        f"API error: {result['error'] or 'none'}\n\n"
        "The official layer's public HTML advertises a 2015–2018 time extent and a field named INDICATED_SALES_PRICE. This is metadata, not confirmation of arms-length sale prices. A live JSON response and full scan are required before empirical counts can be claimed.\n"
    )
