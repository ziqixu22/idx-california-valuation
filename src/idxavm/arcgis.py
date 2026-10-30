"""ArcGIS client. No private data or credentials are required."""
import json
import logging
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

LOG = logging.getLogger(__name__)
LAYER = "https://mapservices.gis.saccounty.gov/arcgis/rest/services/ASSESSOR/MapServer/1"


class ArcGISError(RuntimeError):
    pass


class ArcGISClient:
    def __init__(self, layer=LAYER, retries=3, timeout=20, delay=0.25):
        self.layer, self.retries, self.timeout, self.delay = layer.rstrip("/"), retries, timeout, delay

    def get(self, endpoint="", **params):
        url = self.layer + endpoint + "?" + urlencode({"f": "json", **params})
        for attempt in range(self.retries):
            try:
                with urlopen(Request(url, headers={"User-Agent": "idxavm-research/0.1"}),
                             timeout=self.timeout) as response:
                    result = json.load(response)
                if "error" in result:
                    raise ArcGISError(f"ArcGIS error: {result['error']}")
                return result
            except (HTTPError, URLError, TimeoutError, OSError, ValueError, ArcGISError) as exc:
                if attempt == self.retries - 1 or isinstance(exc, ArcGISError) and "400" in str(exc):
                    raise ArcGISError(f"Request failed after {attempt + 1} attempt(s): {type(exc).__name__}: {exc}") from exc
                LOG.warning("ArcGIS request retry %s/%s: %s", attempt + 1, self.retries, exc)
                time.sleep(min(2 ** attempt, 8))
        raise AssertionError("unreachable")

    def metadata(self):
        return self.get()

    def count(self):
        result = self.get("/query", where="1=1", returnCountOnly="true")
        if not isinstance(result.get("count"), int):
            raise ArcGISError("Count response missing integer count")
        return result["count"]

    def iter_features(self, metadata, fields, total, page_size=None):
        oid = metadata["objectIdField"]
        if not metadata.get("advancedQueryCapabilities", {}).get("supportsPagination"):
            raise ArcGISError("Layer does not support offset pagination")
        size = min(page_size or 1000, metadata.get("maxRecordCount", 1000))
        if size < 1:
            raise ArcGISError("Invalid page size")
        seen = set()
        for offset in range(0, total, size):
            result = self.get("/query", where="1=1", outFields=",".join(fields),
                              returnGeometry="false", orderByFields=f"{oid} ASC",
                              resultOffset=offset, resultRecordCount=size)
            features = result.get("features")
            if not isinstance(features, list) or not features:
                raise ArcGISError(f"Empty or malformed page at offset {offset}")
            for feature in features:
                attrs = feature.get("attributes")
                if not isinstance(attrs, dict) or attrs.get(oid) is None:
                    raise ArcGISError(f"Missing attributes/{oid} at offset {offset}")
                if attrs[oid] in seen:
                    raise ArcGISError(f"Repeated {oid}={attrs[oid]}; source may have changed")
                seen.add(attrs[oid])
                yield attrs
            if len(features) != min(size, total - offset):
                raise ArcGISError(f"Page length mismatch at offset {offset}; source may have changed")
            time.sleep(self.delay)
        if len(seen) != total:
            raise ArcGISError(f"Count changed during scan: expected {total}, got {len(seen)}")
        if self.count() != total:
            raise ArcGISError("Source count changed during scan; retry from a fresh snapshot")
