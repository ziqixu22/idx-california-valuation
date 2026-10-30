"""Run with `python -m unittest discover -s tests` or pytest."""

import tempfile
import unittest
from pathlib import Path

from idxavm.arcgis import ArcGISClient
from idxavm.audit import audit, price, write_report
from idxavm.layers import require_gate


class MockClient(ArcGISClient):
    def __init__(self, pages=None, total=2):
        super().__init__(delay=0)
        self.pages = pages or [
            [
                {
                    "attributes": {
                        "OBJECTID": 1,
                        "Property_Type": "Single Family Residence",
                        "INDICATED_SALES_PRICE": "$250,000",
                        "DOCUMENT_DATE": 1451692800000,
                        "PARCEL_NUMBER": "test",
                        "DOCUMENT_PAGE": "1",
                    }
                }
            ],
            [
                {
                    "attributes": {
                        "OBJECTID": 2,
                        "Property_Type": "Other",
                        "INDICATED_SALES_PRICE": "0",
                        "DOCUMENT_DATE": 1451779200000,
                        "PARCEL_NUMBER": "test2",
                    }
                }
            ],
        ]
        self.total = total

    def get(self, endpoint="", **params):
        if not endpoint:
            return {
                "fields": [
                    {"name": n, "type": "esriFieldTypeString"}
                    for n in (
                        "OBJECTID",
                        "Property_Type",
                        "INDICATED_SALES_PRICE",
                        "DOCUMENT_DATE",
                        "PARCEL_NUMBER",
                    )
                ],
                "objectIdField": "OBJECTID",
                "maxRecordCount": 1,
                "advancedQueryCapabilities": {"supportsPagination": True},
            }
        if "returnCountOnly" in params:
            return {"count": self.total}
        return {"features": self.pages[params["resultOffset"]]}


class FoundationTests(unittest.TestCase):
    def test_mock_audit_and_report(self):
        result = audit(MockClient())
        self.assertEqual(result["counts"]["single_family"], 1)
        self.assertEqual(result["counts"]["valid_positive_prices"], 1)
        self.assertEqual(result["decision"], "NO-GO")
        with tempfile.TemporaryDirectory() as folder:
            write_report(result, Path(folder))
            self.assertTrue((Path(folder) / "data_audit.json").exists())

    def test_duplicate_object_id_fails_closed(self):
        mock = MockClient()
        mock.pages[1][0]["attributes"]["OBJECTID"] = 1
        self.assertIn("Repeated OBJECTID", audit(mock)["error"])

    def test_partial_page_fails_closed(self):
        mock = MockClient(total=3)
        mock.pages.append([])
        self.assertIn("Empty or malformed page", audit(mock)["error"])

    def test_prices(self):
        for raw, expected in [
            ("$1,200.50", "1200.50"),
            ("0", None),
            ("NaN", None),
            ("junk", None),
            (None, None),
        ]:
            self.assertEqual(str(price(raw)) if price(raw) else None, expected)

    def test_gate(self):
        with self.assertRaisesRegex(ValueError, "Live API audit"):
            require_gate({"status": "NOT VERIFIED"}, True)
        with self.assertRaisesRegex(ValueError, "source terms"):
            require_gate({"status": "VERIFIED API COUNTS", "decision": "GO"}, False)
        with self.assertRaisesRegex(ValueError, "Phase 0 decision"):
            require_gate({"status": "VERIFIED API COUNTS", "decision": "NO-GO"}, True)


if __name__ == "__main__":
    unittest.main()
