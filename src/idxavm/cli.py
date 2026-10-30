import argparse
import logging
from pathlib import Path

from .audit import audit, write_report


def main():
    parser = argparse.ArgumentParser(prog="idxavm")
    parser.add_argument("--log-level", default="INFO")
    command = parser.add_subparsers(dest="command", required=True)
    command.add_parser("audit-data")
    ingestion = command.add_parser("ingest")
    ingestion.add_argument("--source", choices=["sacramento"], required=True)
    ingestion.add_argument("--reuse-approved", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(
        level=args.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    if args.command == "audit-data":
        output = Path("reports")
        result = audit()
        write_report(result, output)
        print(f"Audit: {result['status']}; {result['decision']}; see {output / 'data_audit.md'}")
        return 0 if result["status"].startswith("VERIFIED") else 2
    if args.command == "ingest":
        import json

        from .arcgis import ArcGISClient
        from .layers import ingest

        report = json.loads(Path("reports/data_audit.json").read_text())
        print(
            json.dumps(ingest(ArcGISClient(), Path("data"), report, args.reuse_approved), indent=2)
        )
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
