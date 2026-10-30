# Sacramento data audit

**Status:** NOT VERIFIED  
**Decision:** NO-GO

Checked UTC: 2026-10-30T03:16:32.204702+00:00

## Sources

- https://mapservices.gis.saccounty.gov/arcgis/rest/services/ASSESSOR/MapServer/1
- https://assessor.saccounty.gov/us/en/maps-property-data-and-records/assessor-records.html

## Results

```json
{
  "counts": null,
  "field_names": null,
  "property_types": null,
  "date_range": null,
  "geography": null,
  "metadata_sha256": null
}
```

## Blockers

The official assessor records page calls assessor-collected market comparable sales data confidential. Public layer presence does not establish bulk reuse permission or arms-length sale semantics; written clarification required.

API error: ArcGISError: Request failed after 3 attempt(s): URLError: <urlopen error [Errno 8] nodename nor servname provided, or not known>

The official layer's public HTML advertises a 2015–2018 time extent and a field named INDICATED_SALES_PRICE. This is metadata, not confirmation of arms-length sale prices. A live JSON response and full scan are required before empirical counts can be claimed.
