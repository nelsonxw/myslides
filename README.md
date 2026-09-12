# MySlides AI - Executive One-Page PowerPoint Studio

MySlides is an AI application that scrubs, indexes, and analyzes PowerPoint templates from online sources and local decks, learns what makes an effective corporate slide, and generates pixel-perfect, downloadable one-page `.pptx` presentations matching user prompts through an interactive preview-and-refine loop.

---

## Key Features

1. **Automated Template Library & Scrapers**
   - Automatically ingests and indexes `.pptx` files.
   - Built-in scrapers for **SlidesCarnival (CC BY)**, **Microsoft Create**, **GitHub Open Source PPTX**, and **Local Brand Templates**.
   - Allows users to register new URLs or folders directly from the web interface.

2. **Design Learning & Quality Scoring Agent**
   - Evaluates slide effectiveness across 3 key pillars:
     - **Visuals**: Charts, graphs, Fluent UI icons, diagrams, and infographic elements.
     - **Layout & Structure**: Alignment, whitespace ratio (30-55% optimal), spacing consistency, visual hierarchy, and logical reading flow.
     - **Design & Formatting**: Font count (1-2 families), font size scaling tiers, color palette harmony, and WCAG contrast.
   - Synthesizes top-quartile slides into a living `design_rules.json` knowledge bundle.

3. **Prompt-to-Slide Generation & Iteration Loop**
   - Natural language prompting converts intent into structured `SlideIntentSpec` and archetype selection (`kpi_summary`, `timeline`, `comparison`, `data_chart`, `process`).
   - Retrieves top matching exemplars from the library.
   - Compiles and validates layout bounds on a 16:9 widescreen canvas.
   - Native `.pptx` generation using corporate template layouts and Fluent UI icons.
   - **Interactive Website Loop**: Shows 1080p slide preview, asks if changes are needed, updates iterations seamlessly, and allows one-click `.pptx` download.

---

## Quick Start

### 1. Install Dependencies
```bash
cd myslides
pip install -e .
```

### 2. Build Frontend
```bash
npm.cmd --prefix frontend run build
```

### 3. Seed Library (Optional)
```bash
python scripts/seed_library.py
```

### 4. Launch the Application
Double-click `run_app.bat` or execute:
```bash
python -m uvicorn myslides.web.app:create_app --port 8000 --reload --factory
```
Then navigate to **`http://localhost:8000`** in your browser.

---

## Testing & Verification

```bash
# Run backend test suite
python -m pytest tests

# Build React frontend
npm.cmd --prefix frontend run build
```
