# SEC Data Quality Demo

An offline, reproducible example of financial data validation, adapted from the PROYE research screener. It uses one Apple 10-K (accession `0000320193-24-000123`) extracted from an existing SEC 2024q4 Financial Statement Data Sets ZIP. No account, API key, Colab mount, or large download is required.

## Run

Python 3.12 was used for verification. From this folder:

```sh
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python demo.py
python -m unittest discover -s tests -v
```

Alternatively, use `.venv\Scripts\python.exe` directly if PowerShell activation is unavailable. For Google Colab, upload the extracted repository folder, change the working directory to it, then run `!pip install -r requirements.txt`, `!python demo.py`, and `!python -m unittest discover -s tests -v`.

## What this demonstrates

- File integrity checks against SHA-256 provenance records.
- Required columns, document references and taxonomy reference checks.
- Duplicate records, conflicting values and invalid numbers block processing.
- Separate units, periods and reporting contexts; missing observations remain missing.
- Eight selected annual concepts with source candidates and rule-level audit records.
- Ten automated tests, including deliberately corrupted copies of the sample.

The sample includes 1 SUB row, 416 NUM rows, 98 PRE rows and 89 TAG definitions. SUB contains selected metadata columns only; addresses and contacts were excluded. NUM/PRE preserve all rows for the selected accession. See `data/provenance.json` for source, selection, hashes and original module hashes.

## Results

`outputs/quality_report.json` summarizes structural checks. `metrics.csv` contains selected metrics; `metric_audit.csv` records resolution and missing-data status; `evidence.csv` retains candidate rows. The supplied sample passes structural checks and resolves eight concepts. This is not a certification that every financial interpretation is correct.

The original metric engine retains Spanish identifiers and status labels:

| Status | Meaning |
|---|---|
| OK_HECHO_DIRECTO | A unique usable reported value was found |
| OK_REGLA_DOCUMENTADA | An explicit rule resolved the concept |
| SIN_HECHO | Current rules found no usable observation |
| AMBIGUO | Conflicting candidates require investigation |
| PENDIENTE | Human review remains necessary |

## Investigation procedure

On a blocked check, inspect the source table and accession, identify the affected tag and context, and compare with the exact issuer filing. Record the discrepancy, impact and supporting evidence before changing a rule. Never repair an unknown by substituting zero or choosing a convenient candidate. A check that passes does not replace source reconciliation.

## Scope and limitations

This is an educational Data Quality demo, not an investment recommendation, production system or backtest. The bundled filing is historical. FSDS dates may be rounded to month end; do not interpret `20240930` as Apple's exact fiscal closing date. This demo does not implement amendments, filing freshness, full XBRL context reconciliation, universal sector rules, market-data joins or SLA monitoring. PRE may have multiple presentation rows per fact; the engine retains original facts and selects unique values rather than summing joined rows. Rules for other accessions in the inherited modules have not been revalidated by this sample.

The original project's reported 71 quarters and 5.6 GB are not claims made by this demo. Current verification is documented separately from historical reports. No candidate CV, private notebooks, local paths or account details belong in this repository.

## AI assistance and authorship

The original research workflow and this portfolio adaptation were developed with Codex/AI assistance. AI assisted implementation, debugging, documentation and test construction. Automated tests provide specific evidence, not proof of independent human proficiency or universal correctness. The candidate should be able to explain the data model, decisions, failure cases and limitations before presenting the work.

## License and data

Project code is provided under the MIT license in `LICENSE`. SEC sample data and third-party library rights are addressed in `DATA_SOURCES.md`; the code license does not relicense third-party material. This project is not affiliated with S&P Global, Apple or the SEC.
