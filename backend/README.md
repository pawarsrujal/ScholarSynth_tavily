# ScholarSynth Backend

FastAPI backend for multi-agent deep research system.

## Setup

1. Create virtual environment:
```bash
python -m venv venv
venv\Scripts\activate  # Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create `.env` file:
```bash
GEMINI_API_KEY=your_api_key_here
```

4. Run server:
```bash
python main.py
# or
uvicorn main:app --reload
```

Server runs at http://localhost:8000

## API Documentation

Interactive API docs available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Architecture

- **main.py**: FastAPI app and routes
- **graph.py**: LangGraph workflow orchestration
- **models.py**: Pydantic data models
- **memory.py**: In-memory state storage
- **agents/**: Research agent implementations
- **llm/**: Gemini client and prompts

## Testing API

```bash
# Create a research task
curl -X POST http://localhost:8000/api/report \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the latest advances in quantum computing?"}'

# Get status
curl http://localhost:8000/api/report/{task_id}/status

# Get final report
curl http://localhost:8000/api/report/{task_id}
```
