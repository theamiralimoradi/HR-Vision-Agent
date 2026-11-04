# Security and publication checklist

- The private `.env` file from the original project is excluded from this distribution.
- Copy `.env.example` to `.env`, supply your own credentials, and keep the resulting file local.
- **Revoke or rotate the API key present in the original archive.** Removing credentials from a new commit does not invalidate them.
- Do not commit resumes, candidate personal data, analysis reports, local SQLite databases, logs, generated exports, or environment files.
- `hse_policy.json` includes a sample geotechnical/construction recruiting policy. Adapt criteria and review organization-specific details.
- Review `git status` and run an independent secrets scan before publishing or sharing forks.
- If a sensitive value was ever pushed to GitHub, rotate it even if the file was deleted: earlier Git history may still contain it.
- LLM requests may transmit applicant documents to the configured service. Obtain required permissions and comply with applicable privacy and employment requirements.
