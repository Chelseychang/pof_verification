# POF H5 SDK + Local API Demo

This package contains:

- `backend/`: FastAPI mock POF Verification API running on `localhost:8000`
- `frontend/`: H5 page and browser SDK
- `docs/`: quick API notes

## 1. Start API

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Open:

```text
http://localhost:8000/docs
http://localhost:8000/health
```

## 2. Start H5 page

Open `frontend/index.html` directly in browser, or start a static server:

```bash
cd frontend
python -m http.server 5173
```

Then open:

```text
http://localhost:5173
```

Default API address in the page is:

```text
http://localhost:8000
```

## Notes

This is a demo/mock API. It does not perform real face verification. It returns simulated scores for SDK/H5 integration testing.
