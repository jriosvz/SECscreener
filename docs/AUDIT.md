# Verification performed on 2026-11-03

The portfolio demo was assembled from the actual PROYE source modules and a local SEC ZIP. It is not a claim based only on a conversation summary.

- Original project: 34 automated tests passed in a copied workspace using Python 3.12, pandas 3.0.1, NumPy 2.3.5 and PyArrow 23.0.1. These versions differ from the original project's dependency pins; this does not prove every original environment is reproducible.
- Demo: 11 tests passed. Structural checks passed on the bundled real sample; 7 concepts resolved directly and CAPEX resolved through an explicit rule.
- Sample: 604 total rows across four projected/selected tables. Hashes and accession selection are recorded in `data/provenance.json`.
- Historical data inventory: metadata row counts of 28 local Parquet files matched their manifests (31,784,282 rows, 448,639,180 bytes across seven selected quarters). This was a metadata check, not a new cell-by-cell audit of all historical data. These bulk files are not distributed here.
- Privacy review: distribution excludes original notebooks, outputs, contact identities used for SEC requests, local paths, bulk Parquet, ZIP sources, CV and credentials.

Read the README for scope. Test success does not establish universal accounting correctness, financial performance or the candidate's independent proficiency.

Windows clone verification exposed automatic newline conversion. `.gitattributes` now preserves TSV bytes and an additional test checks file integrity against the provenance manifest.
