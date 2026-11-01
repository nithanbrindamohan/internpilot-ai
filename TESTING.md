# InternPilot AI automated test suite

The tests are isolated: they use temporary SQLite databases, temporary resume storage, mock job feeds, and fake OpenAI responses. They do not use the real `.env`, live user databases, employer APIs, or OpenAI credits.

In PowerShell from the project root:

```powershell
cd E:\internpilot-ai
& .\.venv\Scripts\Activate.ps1
python -m pip install pytest httpx
python -m pytest tests -v
```

For the original source adapter tests (also offline, if present):

```powershell
cd E:\internpilot-ai\backend
python -m unittest discover -s tests -v
```

Do not point these tests at your production database or use real API keys. The test fixture explicitly patches the database path and upload directory.

Current coverage: registration, invitation reuse, login, invalid tokens, profile isolation, resume upload/validation, job retrieval, mocked discovery, application ownership, mock AI match and cover-letter generation.

Browser/UI flows require a separate Playwright suite and are **not** covered by these tests. Live employer availability requires running the health checker separately; this is not part of the isolated test suite.
