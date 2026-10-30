"""Reproducible data layer boundaries; writes require explicit verified reuse approval."""
import hashlib
import json
from pathlib import Path

from .arcgis import ArcGISClient
from .audit import price


def require_gate(report, reuse_approved):
    if not report.get("status", "").startswith("VERIFIED"):
        raise ValueError("Live API audit must complete before ingestion")
    if not reuse_approved:
        raise ValueError("Confirm source terms and authorized bulk reuse before ingestion")


def ingest(client: ArcGISClient, root: Path, report: dict, reuse_approved=False):
    require_gate(report, reuse_approved)
    metadata = client.metadata()
    total = client.count()
    fields = [f["name"] for f in metadata["fields"] if f["type"] != "esriFieldTypeGeometry"
              and not f["name"].startswith("Shape.") and not f["name"].startswith("SITUS_")]
    oid = metadata["objectIdField"]
    if oid not in fields or "INDICATED_SALES_PRICE" not in fields:
        raise ValueError("Source schema changed; rerun audit")
    rows = list(client.iter_features(metadata, fields, total))
    raw = "\n".join(json.dumps(row, sort_keys=True) for row in rows).encode() + b"\n"
    digest = hashlib.sha256(raw).hexdigest()
    bronze = root / "bronze" / f"sacramento-{digest}.jsonl"
    bronze.parent.mkdir(parents=True, exist_ok=True)
    if bronze.exists() and bronze.read_bytes() != raw:
        raise ValueError("Immutable snapshot hash collision")
    if not bronze.exists():
        bronze.write_bytes(raw)
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise RuntimeError("Install project dependencies for Parquet output: uv sync") from exc
    clean = []
    exclusions = {}
    for row in rows:
        reason = "invalid_price" if price(row.get("INDICATED_SALES_PRICE")) is None else None
        if reason:
            exclusions[reason] = exclusions.get(reason, 0) + 1
        clean.append({"object_id": row[oid], "price_usd": float(price(row.get("INDICATED_SALES_PRICE"))) if not reason else None,
                      "document_date_ms": row.get("DOCUMENT_DATE"), "property_type": row.get("Property_Type"),
                      "exclusion_reason": reason})
    silver = root / "silver" / f"sacramento-{digest}.parquet"
    silver.parent.mkdir(parents=True, exist_ok=True)
    if not silver.exists():
        pq.write_table(pa.Table.from_pylist(clean), silver)
    manifest = {"source": client.layer, "bronze_sha256": digest, "total": total,
                "silver_rows": len(clean), "exclusions": exclusions,
                "gold_status": "BLOCKED: point-in-time feature policy is Phase 2"}
    (root / "bronze" / f"sacramento-{digest}.manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest
