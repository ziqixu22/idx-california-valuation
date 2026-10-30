# Data provenance and licensing gate

- Candidate official layer: https://mapservices.gis.saccounty.gov/arcgis/rest/services/ASSESSOR/MapServer/1
- Public records policy: https://assessor.saccounty.gov/us/en/maps-property-data-and-records/assessor-records.html

The layer's public HTML identifies `INDICATED_SALES_PRICE` as a string and a 2015–2018 time extent. This does not prove that the number is a market sale, an arms-length transaction, or usable for bulk redistribution. The assessor's public records page lists assessor-collected market comparable sales as confidential. Resolve this apparent conflict with the county before bulk ingestion or publication. Geometry is parcel polygon in EPSG:2226 (reported layer spatial reference 102642/2226). Publication date and historical feature availability are unverified.

