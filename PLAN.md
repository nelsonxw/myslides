---
agent: devin-local
session: fortunate-barometer
created: 2026-09-10T19:50:40Z
---
# MySlides: AI-Assisted One-Page Slide Generator

Build `myslides/` — a FastAPI + React app that scrapes/ingests PowerPoint templates into a scored library, learns what makes a slide effective, and turns a user prompt into a downloadable one-page `.pptx` with an iterative preview loop.

---

## Decisions (from clarification)

| Decision | Choice | Notes |
|---|---|---|
| Preview rendering | **PowerPoint COM via pywin32** (option a) | PowerPoint is installed at `C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE`. Renderer is behind a `SlideRenderer` protocol so an HTML/SVG fallback can be added later. |
| LLM backend | **Dell Dev GenAI gateway** (option a) | Port `LLMClient`/`llm_auth` pattern from `project-tracker/src/project_tracker/utils/` (openai SDK + `aia-auth-client`, base URL `https://aia.gateway.dell.com/genai/dev/v1`, model `gpt-oss-120b`). Behind an `LLMProvider` protocol. |
| Frontend | **React + Vite + TypeScript** (option a) | Mirrors `project-tracker/frontend` (vite 5, react 18, vitest, playwright, esbuild-wasm override). |
| Scrape sources | Microsoft Create, GitHub open-source `.pptx`, SlidesCarnival (CC BY), local `../ppt/templates` + `../ppt/output` | Only license-permissive sources; store license + attribution per asset. |

> The user answered "a" to the first three questions; interpreted as option (a). Confirm at implementation kickoff.

## Environment facts (verified)

- Python 3.14.3 with all needed packages already installed globally: `python-pptx 1.0.2`, `fastapi`, `uvicorn`, `openai 2.38`, `aia-auth-client`, `pillow`, `beautifulsoup4`, `requests`, `httpx`, `playwright`, `pywin32 312`, `comtypes`, `SQLAlchemy 2.0`, `pydantic 2`, `python-dotenv`, `pytest`, `numpy`, `matplotlib`.
- Node v25.9.0; `npm.ps1` blocked by execution policy -> **always call `npm.cmd`** (same as project-tracker AGENTS.md).
- No LibreOffice. PowerPoint present.
- `myslides/` exists and is empty.
- Reusable brand knowledge in `ppt/.devin/skill.md` (Dell colors, fonts, layout indices, `delete_slide` helper, "never set font.name on placeholders").

---

## Architecture

```
myslides/
├── pyproject.toml                 # package "myslides", deps pinned to installed versions
├── .env.example                   # CLIENT_ID, CLIENT_SECRET, USE_SSO, MYSLIDES_DATA_DIR, MYSLIDES_LLM_MODEL
├── .gitignore                     # data/, node_modules/, dist/, __pycache__
├── README.md / AGENTS.md
├── run_app.bat                    # uvicorn + opens browser (same style as project-tracker)
├── src/myslides/
│   ├── config.py                  # Settings (pydantic-settings style, env driven), data dir layout
│   ├── llm/
│   │   ├── provider.py            # LLMProvider protocol: complete(messages, json_schema=None) -> str/dict
│   │   ├── dell_gateway.py        # port of project_tracker LLMClient + llm_auth
│   │   └── prompts/               # *.md prompt templates (intent, compose, critique, revise)
│   ├── library/
│   │   ├── models.py              # SQLAlchemy: Source, TemplateAsset, SlideRecord, SlideFeatures, SlideScore, DesignRule
│   │   ├── repository.py          # CRUD + queries (search by tags/features, top-N by score)
│   │   ├── ingest.py              # .pptx -> TemplateAsset + one SlideRecord per slide (+ thumbnail via renderer)
│   │   └── dedupe.py              # sha256 of file + per-slide structural hash
│   ├── scrapers/
│   │   ├── base.py                # SourceScraper protocol: discover(limit) -> Iterable[AssetLink]; download(link) -> Path
│   │   ├── microsoft_create.py    # create.microsoft.com PowerPoint template listing -> .pptx
│   │   ├── slidescarnival.py      # slidescarnival.com (CC BY) -> .pptx download links
│   │   ├── github_pptx.py         # GitHub code search API `extension:pptx`, filter permissive LICENSE
│   │   ├── local_folder.py        # any folder (seed: ../ppt/templates, ../ppt/output)
│   │   ├── generic_url.py         # user-added URL: direct .pptx link or page crawled for .pptx anchors
│   │   ├── registry.py            # maps Source.kind -> scraper; user-added sources persisted in DB
│   │   └── runner.py              # run all enabled sources: discover -> download -> ingest -> analyze; robots.txt + rate limit
│   ├── analysis/
│   │   ├── extractor.py           # python-pptx -> SlideFeatures (shapes w/ bbox, type, text runs, fonts, sizes, colors, fills, images, charts, tables, groups, z-order)
│   │   ├── metrics/
│   │   │   ├── visuals.py         # counts/ratios: charts, images, icons (small square pictures / svg), diagrams (connector+shape groups), tables, infographic heuristic
│   │   │   ├── layout.py          # alignment score (shared x/y edges), whitespace ratio, spacing consistency (gap stddev), visual hierarchy (distinct font-size tiers), reading flow (top-left -> bottom-right ordering of text blocks), margin adherence
│   │   │   └── formatting.py      # font family count, size scale ratios, palette extraction (k-means on fills/text), WCAG contrast of text vs. background, styling consistency (bullet/shape style variance)
│   │   ├── scorer.py              # weighted composite 0-100 with per-dimension breakdown (weights in design_rules.json, tunable)
│   │   ├── knowledge.py           # aggregates top-quartile slides -> DesignRule table + data/knowledge/design_rules.json (e.g. fonts<=2, whitespace 30-50%, 3-5 palette colors, min contrast 4.5, title 28-40pt, body 14-20pt, archetype layouts)
│   │   └── llm_critic.py          # LLM reads features + preview PNG (if multimodal) -> qualitative strengths/weaknesses, tags (archetype: comparison, timeline, KPI, process, agenda...)
│   ├── generation/
│   │   ├── spec.py                # pydantic SlideSpec (purpose, audience, archetype, key messages, data points, tone, brand) and SlideBlueprint (layout, shapes[], text, chart data, palette, fonts)
│   │   ├── intent.py              # user prompt -> SlideSpec (LLM, JSON-schema constrained)
│   │   ├── retrieval.py           # SlideSpec -> top-K matching library slides (archetype tag match + feature-vector cosine + score)
│   │   ├── composer.py            # SlideSpec + exemplars + DesignRules -> SlideBlueprint (LLM), then rule-based validation/auto-fix (contrast, font tiers, margins)
│   │   ├── builder.py             # SlideBlueprint -> .pptx via python-pptx (base template: Dell template or blank 16:9; charts via pptx chart API; icons from ../ppt Fluent catalog)
│   │   └── revision.py            # (previous Blueprint, user feedback) -> new Blueprint (LLM diff), re-validated
│   ├── rendering/
│   │   ├── base.py                # SlideRenderer protocol: render(pptx_path, slide_index) -> png_path
│   │   └── powerpoint_com.py      # win32com Presentations.Open(WithWindow=False) -> Slide.Export(png, width=1920); single-threaded lock; COM init per thread
│   ├── sessions/
│   │   ├── models.py              # GenerationSession, SlideVersion (blueprint json, pptx path, png path, feedback, created_at)
│   │   └── service.py             # create session -> generate v1; iterate(feedback) -> vN; finalize -> download path
│   └── web/
│       ├── app.py                 # FastAPI, CORS, static mount of frontend/dist
│       ├── schemas.py             # pydantic request/response models
│       └── routers/
│           ├── sources.py         # GET/POST/DELETE /api/sources, POST /api/sources/{id}/run
│           ├── library.py         # GET /api/library/slides?query&archetype&min_score, GET /api/library/slides/{id}/preview.png, GET /api/knowledge/rules
│           ├── generate.py        # POST /api/sessions {prompt} -> v1; POST /api/sessions/{id}/iterate {feedback} -> vN; GET /api/sessions/{id}
│           └── downloads.py       # GET /api/sessions/{id}/versions/{n}/download (.pptx), /preview.png
├── frontend/                      # React + Vite + TS
│   └── src/
│       ├── App.tsx                # routes: Create, Library, Sources
│       ├── pages/CreatePage.tsx   # prompt box -> preview card -> "Need changes?" (Yes: feedback textarea / No: Download) + version strip
│       ├── pages/LibraryPage.tsx  # thumbnails grid, score badges, dimension breakdown, filters
│       ├── pages/SourcesPage.tsx  # list/add/remove sources, run scrape, progress
│       ├── api/client.ts          # typed fetch wrappers
│       └── components/            # SlidePreview, ScoreBreakdown, VersionTimeline, FeedbackPanel
├── scripts/
│   ├── seed_library.py            # ingest ../ppt/templates + ../ppt/output, run analysis + knowledge
│   ├── run_scrape.py              # CLI: --source all|name --limit N
│   └── learn.py                   # recompute scores + design_rules.json
├── tests/
│   ├── unit/                      # extractor, metrics, scorer, knowledge, composer validation, builder, revision (LLM mocked)
│   ├── integration/               # ingest fixture .pptx -> DB; API flows with TestClient + fake LLM/renderer
│   └── fixtures/                  # small hand-built .pptx files (good/bad slides)
└── data/ (gitignored)             # library.sqlite, assets/<sha>/, previews/, sessions/, knowledge/design_rules.json
```

### Key data flow

1. **Scrape/ingest**: `runner` -> `scraper.discover()` -> download -> `dedupe` -> `ingest` (split into `SlideRecord`s, thumbnails) -> `extractor` -> `metrics` -> `scorer` -> `llm_critic` (tags) -> DB.
2. **Learn**: `knowledge.build_rules()` aggregates top-quartile slides into `DesignRule`s + `design_rules.json`, consumed by `composer` and `scorer` weights.
3. **Generate**: prompt -> `intent` (SlideSpec) -> `retrieval` (exemplars) -> `composer` (Blueprint, validated) -> `builder` (.pptx) -> `renderer` (PNG) -> `SlideVersion v1`.
4. **Iterate**: feedback -> `revision` (Blueprint vN) -> builder -> renderer -> `SlideVersion vN`. User picks "No changes" -> download `.pptx` of chosen version.

---

## Implementation Steps

### Phase 0 - Scaffold
1. `pyproject.toml` (setuptools, `src/` layout, pytest `pythonpath=["src"]`), `.env.example`, `.gitignore`, `README.md`, `AGENTS.md`, `run_app.bat`.
2. `config.py`: `Settings` from env (`MYSLIDES_DATA_DIR`, `MYSLIDES_LLM_MODEL=gpt-oss-120b`, `MYSLIDES_RENDERER=powerpoint`, `MYSLIDES_BASE_TEMPLATE` default `../ppt/templates/Dell_Brand_PPT_Template_May2025.pptx`).
3. `llm/provider.py` + `llm/dell_gateway.py` (port from project-tracker; add `complete_json()` that enforces JSON output and retries once on parse failure). `FakeLLMProvider` in tests.

### Phase 1 - Library core
4. `library/models.py`, `repository.py` (SQLite via SQLAlchemy; `Base.metadata.create_all` on startup).
5. `library/ingest.py` + `dedupe.py`: open `.pptx`, per-slide record with slide index, layout name, structural hash; copy asset to `data/assets/<sha256>/`.
6. `scrapers/local_folder.py` + `scripts/seed_library.py` seeding from `../ppt`.

### Phase 2 - Scrapers & user sources
7. `scrapers/base.py`, `registry.py`, `runner.py` (robots.txt check, polite delay, max bytes, retries, per-source log).
8. `microsoft_create.py`, `slidescarnival.py`, `github_pptx.py` (GitHub token optional via env; filter repos with MIT/Apache/CC licenses), `generic_url.py`.
9. Sources API (`routers/sources.py`) so users add a URL/folder source, enable/disable, run now; background run via FastAPI `BackgroundTasks` with job status in DB.

### Phase 3 - Analysis: features, metrics, scoring, knowledge
10. `analysis/extractor.py`: normalized shape records (EMU -> inches, slide-relative), text runs with effective font/size/color (resolve placeholder inheritance through layout/master), picture aspect ratio, chart types, connectors/groups.
11. `metrics/visuals.py`, `metrics/layout.py`, `metrics/formatting.py` — each a pure function `SlideFeatures -> dict[str, float]` covering the user's list: charts/graphs, icons, images, diagrams, infographics; alignment, white space, consistent spacing, visual hierarchy, logical reading flow; font choice, font sizes, color palette, contrast, consistent styling.
12. `scorer.py`: normalize metrics to 0-1 with target ranges from `design_rules.json`, weighted sum -> `SlideScore` with breakdown.
13. `knowledge.py`: compute rule ranges from top-quartile slides, write `design_rules.json`, persist `DesignRule` rows; `scripts/learn.py`.
14. `llm_critic.py`: structured JSON (archetype tags, strengths, weaknesses, one-line "why it works"); stored on `SlideRecord`.

### Phase 4 - Rendering
15. `rendering/powerpoint_com.py`: `pythoncom.CoInitialize`, `Dispatch("PowerPoint.Application")`, open hidden, `Slides(i).Export(path,"PNG",1920,1080)`, close; module-level `threading.Lock`; clear errors if PowerPoint missing.
16. Use renderer for library thumbnails during ingest (batch, one PowerPoint instance per run).

### Phase 5 - Generation pipeline
17. `generation/spec.py` (SlideSpec, SlideBlueprint with shape primitives: `text_box`, `bullet_list`, `rect`, `icon`, `image`, `chart(bar|line|pie|column, categories, series)`, `table`, `arrow`, `divider`).
18. `intent.py` (prompt -> SlideSpec), `retrieval.py` (archetype + feature-vector similarity), `composer.py` (LLM -> Blueprint; `validate_blueprint()` auto-fixes overflow, contrast < 4.5, >2 font families, off-margin shapes).
19. `builder.py`: Blueprint -> `.pptx` using base template layout "Title & subtitle only" (idx 29 for Dell template; auto-detect equivalent for other bases), delete template's existing slides, never set `font.name` on placeholders, icons from `../ppt/scripts/executive_examples/icons/all` via catalog lookup.
20. `revision.py`: feedback + prior Blueprint -> new Blueprint (LLM), re-validate; keep change summary for UI.
21. `sessions/service.py`: orchestrates generate/iterate/finalize; stores every version.

### Phase 6 - Web API
22. `web/app.py` + routers (`sources`, `library`, `generate`, `downloads`), `schemas.py`, static mount of `frontend/dist`, CORS for vite dev server.

### Phase 7 - Frontend
23. Vite + React + TS scaffold mirroring project-tracker (`npm.cmd` scripts: dev/build/test/e2e).
24. `CreatePage`: prompt -> loading -> preview PNG + LLM change summary -> "Need any changes?" Yes (feedback box -> new version) / No (Download `.pptx`); version strip to compare/revert.
25. `LibraryPage` (grid, score badge, breakdown tooltip, filters) and `SourcesPage` (CRUD, run, status).

### Phase 8 - Tests, docs, polish
26. Unit tests for metrics with fixture slides (good vs. bad), scorer monotonicity, knowledge rule ranges, blueprint validation/auto-fix, builder output opens with python-pptx and contains expected shapes.
27. Integration tests: ingest fixture -> query API; full session flow with `FakeLLMProvider` + `FakeRenderer`; download returns valid `.pptx`.
28. Frontend vitest for CreatePage state machine; Playwright e2e for prompt -> preview -> iterate -> download.
29. README (setup, `.env`, seeding, running), AGENTS.md (verification commands).

---

## Files to Create (summary)

- `myslides/pyproject.toml`, `.env.example`, `.gitignore`, `README.md`, `AGENTS.md`, `run_app.bat`
- `myslides/src/myslides/**` as per tree above (~35 modules)
- `myslides/frontend/**` (Vite React TS)
- `myslides/scripts/{seed_library,run_scrape,learn}.py`
- `myslides/tests/{unit,integration,fixtures}/**`

No existing files outside `myslides/` are modified; `../ppt` is read-only input.

---

## Verification

- [ ] `python -m pytest tests/unit tests/integration` (uses temp `MYSLIDES_DATA_DIR`; LLM + renderer faked)
- [ ] `python scripts/seed_library.py` ingests Dell template + `ppt/output` decks, produces thumbnails and scores
- [ ] `python scripts/run_scrape.py --source slidescarnival --limit 3` downloads, ingests, scores (network)
- [ ] `python scripts/learn.py` writes `data/knowledge/design_rules.json`
- [ ] `npm.cmd --prefix frontend test`, `npm.cmd --prefix frontend run build`
- [ ] Manual: `run_app.bat`, prompt "quarterly revenue KPI slide for execs", preview shows, request "make chart blue and add 3 takeaways", new preview, download opens in PowerPoint
- [ ] `npm.cmd --prefix frontend run e2e` against backend with temp data dir

---

## Risks / Considerations

- **Scraper fragility & licensing**: site markup changes break scrapers; keep them thin, tested against saved HTML fixtures, and record `license`/`attribution` per asset. Respect robots.txt and rate limits. GitHub API unauthenticated limit is 10 req/min for search — optional token in `.env`.
- **PowerPoint COM**: single-instance, Windows-only, fails in non-interactive sessions/services. Serialize with a lock; surface a clear error; renderer protocol allows an HTML fallback later.
- **LLM JSON reliability**: constrain with schema, validate with pydantic, retry once, then fall back to a rule-based archetype Blueprint so generation never hard-fails.
- **Font inheritance in extraction**: effective font/size requires walking placeholder -> layout -> master; implement carefully with tests, default sensibly when unresolved.
- **"Effectiveness" is heuristic**: scores are transparent (breakdown shown in UI) and weights/ranges live in `design_rules.json` so they can be tuned; LLM critic adds qualitative signal but is not the sole judge.
- **Corporate network/SSO**: Dell gateway needs `CLIENT_ID`/`CLIENT_SECRET` or SSO like project-tracker; never commit `.env`.
- **Python 3.14**: verify `pywin32`/`python-pptx` behave; already installed, so low risk.
