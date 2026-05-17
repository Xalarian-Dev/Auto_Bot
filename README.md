# Auto_Bot — Job Research Multi-Agent System

Automated job research system using Claude AI as a scoring engine.
Fetches, deduplicates, scores, and stores senior IT PM/Director roles across APAC, North America, and Europe.

---

## Quick start

```bash
# Install dependencies
.venv/Scripts/pip install -r requirements.txt

# Copy and fill in your config files
cp .env.example .env
cp assets/candidate.yaml.example assets/candidate.yaml

# Run the scout
.venv/Scripts/python.exe main.py --mode A          # APAC
.venv/Scripts/python.exe main.py --mode B          # North America
.venv/Scripts/python.exe main.py --mode C          # Northern Europe + Paris
.venv/Scripts/python.exe main.py --mode A --dry-run  # Preview without saving
.venv/Scripts/python.exe main.py --top             # Show top listings (all modes)
.venv/Scripts/python.exe main.py --top --mode A    # Show top listings for one mode
.venv/Scripts/python.exe main.py --stats           # DB statistics per mode

# Launch the dashboard
launch.bat
# or manually: .venv/Scripts/streamlit run app.py
```

---

## Setup

### 1. Candidate profile

Copy `assets/candidate.yaml.example` to `assets/candidate.yaml` and fill in your details.
This file contains your personal info, professional summary, and scoring preferences.
It is gitignored and never committed.

### 2. Environment variables

Copy `.env.example` to `.env` and fill in your API keys.

### 3. Mode profiles (optional)

Edit `config/mode_profiles.yaml` to customize search keywords, locations, and sources per mode.
Use the **Mode Editor** tab in the dashboard to edit visually — saves and regenerates `config/criteria.yaml` automatically.

---

## Modes

| Mode | Target | Status |
|------|--------|--------|
| A | APAC (Singapore, HK, AU, JP, HCMC, Bangkok...) | Active |
| B | North America (USA, Canada) | Active |
| C | Northern Europe + Paris | Active (Indeed EU requires paid SerpAPI) |

---

## API Keys required

| Key | Usage | Get it |
|-----|-------|--------|
| `ANTHROPIC_API_KEY` | Claude Haiku scorer + Claude Sonnet drafter | console.anthropic.com |
| `SERPAPI_KEY` | Google Jobs aggregator (see below) | serpapi.com — free tier: 250 searches/month |
| `USAJOBS_KEY` | USAJobs.gov API | developer.usajobs.gov — free registration |
| `USAJOBS_EMAIL` | USAJobs.gov API (User-Agent header) | Same registration as above |

---

### About SerpAPI

SerpAPI is a paid service that queries Google Jobs and returns structured JSON results.
Google Jobs aggregates listings from LinkedIn, Indeed, Glassdoor, Seek, and hundreds of other boards — making SerpAPI the single highest-value source in this project.

- Free tier: 250 searches/month (enough for occasional runs)
- Paid plans start at $50/month for 5,000 searches
- Register and get your key at: https://serpapi.com/
- **Optional** — if no key is configured, SerpAPI and Indeed EU sources are silently skipped. All other sources still work.

---

## Sources — active

| Source | Mode | Method | Notes |
|--------|------|--------|-------|
| SerpAPI / Google Jobs | A, B | API key | Aggregates LinkedIn, Indeed, Glassdoor |
| Jaabz | A, B | HTML scrape, no key | Visa-sponsored + relocation-focused |
| GlobalJobs | A, B, C | HTML scrape, no key | NGO, international org, government IT roles |
| Greenhouse ATS | A, B | Public API, no key | Tech/global companies — see list below |
| USAJobs | B | API key (free) | US federal government IT roles |
| Job Bank Canada | B | HTML scrape, no key | Canadian government portal |
| IT Job Board USA | B | HTML scrape, no key | North America IT-specific board |
| Indeed EU | C | SerpAPI paid engine | Requires paid SerpAPI plan |
| MyCareersFuture | — | Public API, no key | Disabled — requires SingPass (SG citizens only) |

### Greenhouse companies (verified tokens)

| Token | Company | Modes |
|-------|---------|-------|
| `thoughtworks` | Thoughtworks | A, B |
| `gitlab` | GitLab | A, B |
| `airbnb` | Airbnb | A, B |
| `databricks` | Databricks | A, B |
| `stripe` | Stripe | A, B |
| `elastic` | Elastic | A, B |
| `okta` | Okta | A, B |
| `cloudflare` | Cloudflare | A, B |
| `datadog` | Datadog | A, B |
| `canonical` | Canonical | A, B |
| `figma` | Figma | A, B |
| `anthropic` | Anthropic | A, B |
| `riotgames` | Riot Games | A, B |
| `epicgames` | Epic Games | A, B |
| `contentful` | Contentful | A, B |
| `algolia` | Algolia | A, B |
| `braze` | Braze | A, B |
| `twilio` | Twilio | B |
| `mongodb` | MongoDB | B |
| `lyft` | Lyft | B |
| `dropbox` | Dropbox | B |
| `pagerduty` | PagerDuty | B |
| `hubspotjobs` | HubSpot | B |
| `klaviyo` | Klaviyo | B |
| `robinhood` | Robinhood | B |

---

## Sources — Cloudflare protected (blocked)

These boards were attempted but are protected by Cloudflare Bot Management.
Direct HTTP scraping returns 403 or a JS challenge page. Kept here for information — may be worth retrying in the future or covering via SerpAPI if added to Google Jobs index.

| Board | Target | Notes |
|-------|--------|-------|
| Seek (seek.com.au) | AU, NZ, SE Asia | Partially covered via SerpAPI Google Jobs |
| JobsDB (jobsdb.com) | HK, SG, TH, PH | Partially covered via SerpAPI Google Jobs |
| Jobstreet (jobstreet.com) | MY, SG, PH, ID | Partially covered via SerpAPI Google Jobs |
| Jobbatical (jobbatical.com) | Global relocation | Not covered elsewhere |
| Relocate.me / Hiring Without Borders | Global relocation | Same site, not covered elsewhere |
| Careerjet | Global | Requires API key + IP whitelist — skipped |

---

## Sources — backlog (to add)

### Mode A — APAC

| Board | Countries | Access method | Priority |
|-------|-----------|---------------|----------|
| Daijob | Japan | HTTP scrape | Medium — English IT jobs in Japan |
| GaijinPot Jobs | Japan | HTTP scrape | Medium — expat-focused |
| Indeed AU/SG | AU, SG | SerpAPI paid | Low — needs paid plan |
| Xpatjobs | Global | HTTP scrape | Low — old site, worth probing |

### Mode B — North America

| Board | Countries | Access method | Priority |
|-------|-----------|---------------|----------|
| Dice.com | USA | HTTP scrape | Medium — IT-specific, senior roles |
| The Ladders | US, CA | HTTP scrape | Medium — $100k+ roles only |
| ExecThread | US, CA | HTTP scrape | Medium — Director+ level |

### Mode C — Northern Europe + Paris

| Board | Countries | Access method | Priority |
|-------|-----------|---------------|----------|
| Welcome to the Jungle | France | HTTP scrape | High — tech-forward, English-friendly |
| StepStone | NL, BE, DK, FI | HTTP scrape | High — dominant in Northern EU |
| Jobs.lu | Luxembourg | HTTP scrape | Medium — small but targeted |

---

## Architecture

```
Auto_Bot/
├── main.py                      # Entry point + CLI
├── app.py                       # Streamlit dashboard
├── launch.bat                   # One-click dashboard launcher
├── config/
│   ├── mode_profiles.yaml       # Human-readable mode config (edit this)
│   ├── criteria.yaml            # Auto-generated from mode_profiles.yaml
│   └── profile_generator.py    # Generates criteria.yaml from profiles
├── assets/
│   ├── candidate.yaml           # Your personal profile (gitignored)
│   ├── candidate.yaml.example   # Template for new users
│   ├── candidate.py             # Profile loader (used by scorer + drafter)
│   └── *.pdf                    # Your resume (gitignored via data/)
├── data/
│   └── scout.db                 # SQLite database (gitignored)
├── output/                      # Generated PDFs (gitignored)
├── scout/
│   ├── models.py                # Pydantic + SQLAlchemy models
│   ├── db.py                    # Database layer
│   ├── scorer.py                # Claude Haiku relevance scorer
│   ├── runner.py                # Pipeline orchestrator
│   └── sources/
│       ├── base.py              # Base class (retry, HTTP client, region inference)
│       ├── utils.py             # Shared utilities (date parsing, etc.)
│       ├── serpapi.py           # Google Jobs via SerpAPI
│       ├── indeed.py            # Indeed EU via SerpAPI (Mode C)
│       ├── mycareersfuture.py   # Singapore gov portal (disabled)
│       ├── usajobs.py           # USAJobs.gov API (Mode B)
│       ├── jobbank.py           # Job Bank Canada scraper (Mode B)
│       ├── jaabz.py             # Jaabz relocation jobs scraper (Mode A, B)
│       ├── globaljobs.py        # GlobalJobs NGO/international scraper (Mode A, B, C)
│       ├── greenhouse.py        # Greenhouse ATS public API (Mode A, B)
│       └── itjobboard.py        # IT Job Board USA scraper (Mode B)
└── drafter/
    ├── agent.py                 # Claude Sonnet cover letter + talking points
    ├── writer.py                # PDF generator (fpdf2)
    └── resume.py                # PDF resume text extractor (pypdf)
```

### Pipeline flow

```
[main.py --mode X]
    └── expire old listings (auto-ignore NEW listings older than 21 days)
    └── [runner] load config for mode
            └── region filter: drop listings not matching mode's target region
            └── [sources] fetch listings
                    └── [db] deduplicate + persist (tagged with mode)
                            └── [scorer] Claude Haiku scores each new listing
                                    └── [db] store score + notes
                                            └── display per-mode table
```

### Job score interpretation

| Score | Meaning |
|-------|---------|
| 80-100 | Excellent match — apply |
| 60-79 | Good match — worth reviewing |
| 40-59 | Partial match — review if time permits |
| 0-39 | Poor match — skip |

### Job status flow

| Status | Meaning |
|--------|---------|
| Active (new) | Default — visible in dashboard |
| Applied | Manually marked after applying |
| Ignored | Manually dismissed or auto-expired after 21 days |

---

## Drafter agent

Generates a tailored cover letter and resume talking points for any job in the database.

- Triggered from the dashboard — select a job, click "Generate"
- Uses Claude Sonnet (higher quality than Haiku scorer)
- Reads your PDF resume from `assets/` automatically
- Reads candidate profile from `assets/candidate.yaml`
- Cover letter auto-detects language (English or French based on job location)
- Output: editable text in dashboard + downloadable PDF saved to `output/`

---

## Adapting for another user

1. Copy `assets/candidate.yaml.example` → `assets/candidate.yaml` and fill in your details
2. Place your resume PDF in `assets/` (any filename, first PDF found is used)
3. Copy `.env.example` → `.env` and add your API keys
3. Open the **Mode Editor** in the dashboard to set your target keywords, locations, and sources
4. Run the scout

No Python code changes needed.
