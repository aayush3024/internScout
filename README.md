# InternScout — Student Internship Finder (TinyFish)

A vibrant, responsive internship discovery dashboard. Students create a lightweight profile, search the live web with TinyFish, rank results against their skills, save a shortlist, export it to CSV, and inspect listings using TinyFish Fetch and the TinyFish Web Agent.

## Features

- Student profile: role, skills, location, education level and work preference.
- Four targeted TinyFish Search queries per search for broader discovery.
- Explainable relevance score based on skill overlap, internship-related title terms and location match.
- Deduplicated and ranked opportunity cards with original source links.
- Saved shortlist persisted in browser localStorage.
- CSV export for saved opportunities.
- TinyFish Fetch to read a selected listing page.
- TinyFish Web Agent to inspect a selected page and extract role, organization, eligibility, skills, stipend, deadline, duration and application steps.
- API key stays on the Flask server; it is never sent to frontend JavaScript.
- No API key? The dashboard loads, but live search and research need the key.

## TinyFish APIs used

1. **Search** — `GET https://api.search.tinyfish.ai?query=...`
2. **Fetch** — `POST https://api.fetch.tinyfish.ai` with `{"urls":[...],"format":"markdown","links":true}`
3. **Web Agent SSE** — `POST https://agent.tinyfish.ai/v1/automation/run-sse` with `url`, `goal`, and `browser_profile: "lite"`.

All requests authenticate with `X-API-Key`. Search uses the `IN` country code for India while the student's location is included in the search phrase. The agent extracts information only; the app does not auto-apply, create accounts, send emails, or submit personal data.

## Setup (Windows / VS Code)

1. Extract the ZIP and open the `InternScout_TinyFish` folder in VS Code.
2. Open Terminal → New Terminal.
3. Create a virtual environment:

   ```powershell
   python -m venv venv
   ```

4. Activate it:

   ```powershell
   .\venv\Scripts\activate
   ```

   If PowerShell blocks activation:

   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   .\venv\Scripts\activate
   ```

5. Install packages:

   ```powershell
   pip install -r requirements.txt
   ```

6. Create `.env`:

   ```powershell
   Copy-Item .env.example .env
   ```

7. Open `.env` and paste your key:

   ```env
   TINYFISH_API_KEY=your_actual_tinyfish_key
   ```

   Get a key at https://agent.tinyfish.ai/api-keys. Do not share it or commit `.env` to GitHub.

8. Run the app:

   ```powershell
   python app.py
   ```

9. Open http://127.0.0.1:5000

## Demo walkthrough

1. Enter a target role such as `Python Developer Intern`.
2. Add skills separated by commas: `Python, Flask, SQL, Git`.
3. Select a location such as `India` or `Remote`.
4. Click **Find my internships**.
5. Save promising results using the heart button.
6. Click **Research** on a result.
7. Use **Fetch page content** for page text or **Run AI web agent** for structured extraction.
8. Export the shortlist to CSV.

## Matching algorithm

The relevance score is a heuristic, not a machine-learning prediction:
- Up to 65 points for overlap between profile skills and listing title/snippet/source words.
- 20 points when the title contains internship-related terms such as `intern`, `internship`, `trainee` or `fellow` (5 otherwise).
- Up to 15 points for a location match.
- Scores are capped at 99 and sorted descending.

A listing may not mention every skill in its search snippet. Always inspect the original source page and verify eligibility, stipend, dates, location and whether applications are open.

## Project structure

```text
InternScout_TinyFish/
├── app.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── templates/
│   └── index.html
└── static/
    ├── css/style.css
    └── js/app.js
```

## Troubleshooting

- **API key needed:** `.env` must be in the same folder as `app.py`; restart Flask after changing it.
- **401 Unauthorized:** verify the key in TinyFish dashboard.
- **429 Too Many Requests:** wait and retry; Search rate limits depend on account/plan.
- **Agent takes time:** page navigation can take longer than Search; allow up to a few minutes.
- **No results:** try a broader role or location, or simplify skill keywords.
- **PowerShell activation issue:** use the process-scoped execution policy command above.

## Responsible use / limitations

- Search results are web discovery results, not confirmed open vacancies.
- Match scores are approximate keyword heuristics.
- Stipends, deadlines, eligibility and availability must be verified on the original employer/portal page.
- Do not enter passwords, government ID numbers, banking information or other sensitive personal data.
- The application does not auto-apply or submit applications.
