# Zero-Click Store Operator — Hackathon MVP

A working MVP for Track 1: an AI-powered kirana store operator.

## What it does
- Accepts a natural-language customer request.
- AI/rule parser identifies products and quantities.
- Live inventory is read from SQLite.
- Prices and stock are checked before action.
- Order is created in the database.
- Inventory is reduced automatically after order creation.
- Customer receives a structured confirmation.
- Dashboard shows products, stock, orders and low-stock items.
- Includes a deterministic fallback parser so the demo still works without an AI key.

## Stack
- Backend: FastAPI + SQLAlchemy + SQLite
- AI: Google Gemini via `google-genai` (optional)
- Frontend: React + Vite

## Run backend
```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux
uvicorn app.main:app --reload
```

Backend: http://127.0.0.1:8000
Docs: http://127.0.0.1:8000/docs

## Run frontend
```bash
cd frontend
npm install
npm run dev
```

Frontend: http://localhost:5173

## AI configuration
Set `GEMINI_API_KEY` in `backend/.env` to enable Gemini parsing. If it is empty, the app uses a local deterministic parser for the supported demo catalog.

## Demo request
Try:
> 2 Aashirvaad Atta, 1 Fortune Oil and 3 Maggi please

The system will retrieve live prices/stock, calculate the total, create an order, reduce inventory, and return a confirmation.

## Important demo behavior
The order tool is transactional: if any requested item is unavailable or insufficient, the order is not created and inventory is not changed.
