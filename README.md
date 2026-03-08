# Teacher Agents

FastAPI project managed with [uv](https://docs.astral.sh/uv/).

## Setup

```bash
uv sync
```

## Run

```bash
uv run python main.py
```

Or with uvicorn directly:

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

## Full-stack (React + FastAPI)

Start both the frontend and backend with one command:

```bash
npm run dev
```

Then open **http://localhost:5173** for the React app. The API runs at http://localhost:8000; the frontend proxies `/api` and `/health` to it.
