# OptiSolve AI

**AI-powered LP/MILP optimization solver.** Upload any document with a Linear Programming problem. Gemini AI extracts the mathematical formulation. Google OR-Tools finds the optimal solution with full sensitivity analysis.

**[Try it live](https://solver.siftyai.com/app)** | **[Project page](https://siftyai.com/projects/optisolve)**

---

## How It Works

```
Upload document  -->  Gemini AI extracts formulation  -->  OR-Tools solves  -->  Results + Sensitivity
```

1. **Upload** a PDF, image, Word doc, spreadsheet, or text file describing an optimization problem
2. **Gemini AI** reads the document and extracts the full LP/MILP formulation (objective, constraints, bounds, variable types) as structured JSON
3. **Google OR-Tools** solves the problem using GLOP (LP) or SCIP (MILP)
4. **Results** are displayed with mathematical equations, a constraint matrix, decision variable values, and sensitivity analysis

No code required. No sign-up. Bring your own free [Gemini API key](https://ai.google.dev).

---

## Features

- **AI-Powered Extraction** — Gemini reads documents (PDFs, images, spreadsheets) and extracts the complete LP/MILP formulation using a structured chain-of-thought prompt with forced JSON output mode
- **Equation Display** — Extracted formulation rendered as proper mathematical notation: objective function, constraints with operators, variable bounds with integer badges
- **Constraint Matrix** — Excel-like grid view of the full coefficient matrix with relation types and RHS values
- **Sensitivity Analysis** (LP only) — Shadow prices (dual values), reduced costs, slack/surplus, and binding status for every constraint
- **Smart Validation** — Irrelevant documents (resumes, reports, etc.) are rejected before the solver runs. Missing API keys are caught client-side
- **Privacy-First** — Files are processed in memory, uploaded to Gemini temporarily, and deleted immediately. No database, no storage, fully stateless
- **Multiple Solvers** — GLOP for pure LP (with sensitivity), SCIP/CBC for MILP
- **Multiple Gemini Models** — Choose between `gemini-2.5-pro`, `gemini-2.5-flash`, or `gemini-2.0-flash`

---

## Tech Stack

| Component | Technology |
|---|---|
| AI Extraction | Google Gemini 2.5 (JSON mode) |
| Solver | Google OR-Tools (GLOP / SCIP / CBC) |
| Backend | FastAPI + Uvicorn |
| Templates | Jinja2 |
| Frontend | Vanilla JS + Custom CSS |
| Language | Python 3.11 |
| Hosting | Google Cloud Run |

---

## Project Structure

```
app/
├── main.py                 # FastAPI app, mounts static files, templates, routers
├── config.py               # Available models, file size limits, allowed extensions
├── routes/
│   ├── landing.py          # GET /  → landing page
│   ├── app_page.py         # GET /app → solver UI
│   └── api.py              # POST /api/solve → main pipeline endpoint
├── solver/
│   ├── extractor.py        # Gemini file upload + AI extraction call
│   ├── prompt.py           # Chain-of-thought system prompt for LP extraction
│   ├── parser.py           # JSON → validated LP data with kill switch
│   └── engine.py           # OR-Tools solver + sensitivity analysis
├── templates/
│   ├── base.html           # Shared layout (navbar, footer)
│   ├── landing.html        # Marketing landing page
│   └── app.html            # Solver interface
└── static/
    ├── favicon.svg
    ├── css/custom.css
    └── js/solver.js        # File handling, API calls, result rendering
```

---

## Pipeline

```
POST /api/solve (file + api_key + model_name)
        │
        ▼
   extractor.py ── upload file to Gemini Files API
        │            send LP_EXTRACTION_PROMPT + file
        │            receive JSON response
        │            delete Gemini file + temp file
        ▼
    parser.py ──── json.loads() response
        │           check is_valid_lp (kill switch)
        │           validate dimensions, types, bounds
        ▼
    engine.py ──── select solver (GLOP for LP, SCIP for MILP)
        │           build variables, constraints, objective
        │           solver.Solve()
        │           extract values, reduced costs, dual values, slack
        ▼
   JSON response ── { extraction, solution, sensitivity }
        │
        ▼
   solver.js ───── render equations, grid, tables, sensitivity
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- A free Google Gemini API key from [ai.google.dev](https://ai.google.dev)

### Local Development

```bash
# Clone the repo
git clone https://github.com/mohdjun95/optisolve-ai.git
cd optisolve-ai

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

Open [http://localhost:8080](http://localhost:8080) in your browser. Enter your Gemini API key in the app and upload a document.

### Docker

```bash
docker build -t optisolve-ai .
docker run -p 8080:8080 optisolve-ai
```

### Deploy to Cloud Run

```bash
gcloud run deploy optisolve-ai \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8080
```

No server-side environment variables needed — the API key is supplied by each user at runtime.

---

## API

### `POST /api/solve`

Multipart form data:

| Field | Type | Required | Description |
|---|---|---|---|
| `file` | File | Yes | Document containing an LP/MILP problem |
| `api_key` | string | Yes | Google Gemini API key |
| `model_name` | string | Yes | Gemini model (e.g. `gemini-2.5-flash`) |

**Response:**

```json
{
  "success": true,
  "stage": "complete",
  "extraction": {
    "problem_type": "Maximization",
    "variable_names": ["chairs", "tables"],
    "c": [5.0, 7.0],
    "A_ub": [[2, 3], [4, 1], [1, 1]],
    "b_ub": [120, 80, 40],
    "bounds": [[0, null], [0, null]],
    "is_integer_variable": [false, false]
  },
  "solution": {
    "status_str": "OPTIMAL",
    "obj_val": 200.0,
    "var_vals": [
      {"name": "chairs", "value": 10.0, "reduced_cost": 0.0},
      {"name": "tables", "value": 20.0, "reduced_cost": 0.0}
    ],
    "is_pure_lp": true,
    "constraint_details": [
      {"type": "ub", "rhs": 120.0, "slack": 0.0, "dual_value": 1.5}
    ]
  }
}
```

### `GET /health`

Returns `{"status": "ok"}`.

---

## Supported File Types

PDF, PNG, JPG, JPEG, GIF, BMP, TIFF, TXT, DOCX, DOC, XLSX, XLS, CSV (max 50 MB)

---

## License

MIT

---

Built by [Junaid](https://siftyai.com)
