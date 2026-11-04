# HR Vision Agent

**A local, multi-role, AI-assisted resume screening and candidate evaluation application.**

HR Vision Agent combines a Streamlit dashboard, document processing, vision-capable large language models (LLMs), configurable role-specific scoring policies, and a local SQLite cache. It is designed to support human recruiters—not to make autonomous hiring decisions.

## Features

- **Multi-role screening:** create role-specific job descriptions, evaluation criteria, weights, and thresholds; an example construction HSE policy is included.
- **Document ingestion:** process PDF, DOCX, and supported image-based content with model-assisted visual extraction; Tesseract is not required.
- **Evidence-aware scoring:** evaluate experience and skills against the selected role, flag unsupported claims, and avoid double-counting overlapping work periods.
- **Batch evaluation:** analyze multiple applicants, rank results, and generate interview questions.
- **Human review:** inspect and manually correct stored assessments without repeating paid LLM requests.
- **Local caching:** reuse results when the resume, role configuration, model, and processing settings are unchanged.
- **Excel export:** generate a multi-sheet, right-to-left workbook for review and reporting.
- **Privacy controls:** keep resumes and evaluation results on the local computer, except for content explicitly sent to the configured AI provider.

## Technology

Python · Streamlit · SQLite · PyMuPDF · OpenAI-compatible API · pandas · openpyxl

## Quick start (Windows)

1. Install a supported Python version and create/activate a virtual environment.
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and enter your own API key. **Never commit `.env`.**
4. Run `RUN_VISION.bat` or start the application with:

   ```bash
   streamlit run app_vision.py --server.port 8518
   ```
5. Open `http://localhost:8518`.

## Workflow

1. **Roles & policies:** configure positions, criteria, scoring weights, and decision thresholds.
2. **Upload & consent:** submit candidate documents using the browser or the local `inbox/` folder. External AI calls require explicit confirmation in the application.
3. **Evaluate & review:** view comparisons, source-evidence statuses, experience calculations, and manual adjustments.
4. **Export:** download the Excel workbook and examine API usage logs.

## Configuration

| Setting | Purpose |
| --- | --- |
| `GAPGPT_API_KEY` | Your private API credential. Place it only in the local `.env` file. |
| `GAPGPT_BASE_URL` | Base URL of the configured OpenAI-compatible provider. |

The included `hse_policy.json` is an **example policy**, reflecting construction/geotechnical HSE recruitment needs. Adapt the criteria and local requirements before practical use. The application interface and sample evaluation policy are currently primarily in Persian; this repository documentation is in English.

## Data handling and limitations

- Candidate documents, stored model responses, and exports can contain personal data. These must **not** be committed to GitHub.
- The provider receives document content only when the user explicitly starts the AI analysis. Review the provider's data-handling terms before use.
- Scoring is a decision-support heuristic, **not** a verified measure of professional competence or an automated hiring decision.
- AI output may be incorrect or incomplete. Important hiring decisions require human review.
- Model compatibility, image processing accuracy, pricing, token estimates, and Windows execution have **not** been independently end-to-end verified for every environment.
- Previous databases from older application versions are not automatically migrated.

## Testing

Run offline checks:

```bash
python -m unittest discover -s tests -v
python tests/ui_smoke.py
```

These checks do not validate live API access or all browser/PDF workflows.

## Project status

**Experimental / prototype.** Suitable for evaluation and further development; production readiness, security, and compliance require additional validation.

## Security

See [SECURITY_PUBLISHING.md](SECURITY_PUBLISHING.md) before publishing, forking, or deploying. The original private API key is not included. If it was ever exposed or shared, **revoke/rotate it**.

## License

No open-source license has been selected. All rights are reserved unless the repository owner adds a license.
