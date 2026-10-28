# ScholarSynth

A multi-agent deep research system powered by LangGraph and Google Gemini. ScholarSynth generates comprehensive 2000+ word research reports with citations from multiple sources.

## 🌟 Features

- **Multi-Agent Architecture**: Planner → Parallel Executors → Publisher workflow
- **Deep Research**: Generates 6-10 sub-questions and researches each in parallel
- **Comprehensive Reports**: 2000+ word reports with inline citations [S1], [S2]
- **Real-time Progress**: Live updates via Server-Sent Events (SSE)
- **Modern Stack**: FastAPI + LangGraph + Gemini LLM + React + TypeScript
- **In-Memory Storage**: No database required - everything stored in memory

## 🏗️ Architecture

```
User Query
    ↓
┌─────────────┐
│   Planner   │  → Breaks query into 6-10 sub-questions
└─────────────┘
    ↓
┌─────────────┐
│  Executors  │  → Parallel research for each sub-question
│  (Parallel) │  → Retrieves sources, summaries, citations
└─────────────┘
    ↓
┌─────────────┐
│  Publisher  │  → Synthesizes all research into final report
└─────────────┘
    ↓
Final Report (2000+ words with citations)
```

## 📋 Prerequisites

- Python 3.10 or higher
- Node.js 18+ and npm
- Google Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))

## 🚀 Quick Start

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment:
```bash
python -m venv venv

# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your Gemini API key:
```bash
copy .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

5. Start the backend server:
```bash
python main.py
```

The backend will run at `http://localhost:8000`

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

The frontend will run at `http://localhost:3000`

## 📡 API Endpoints

### `POST /api/report`
Create a new research task
```json
{
  "query": "What are the latest advances in quantum computing?"
}
```

### `GET /api/report/{task_id}/status`
Get task status and progress

### `GET /api/report/{task_id}`
Get complete task state including final report

### `GET /api/report/{task_id}/stream`
Server-Sent Events stream for real-time progress updates

### `GET /api/reports`
List all active research tasks

### `DELETE /api/report/{task_id}`
Delete a research task

## 🧪 Example Queries

- "What are the environmental impacts of blockchain technology?"
- "How is CRISPR gene editing being used in cancer treatment?"
- "What are the latest advances in quantum computing and their implications for cryptography?"
- "What are the ethical implications of AI in autonomous vehicles?"

## 🔧 Project Structure

```
ScholarSynth/
├── backend/
│   ├── agents/
│   │   ├── planner.py      # Sub-question generation
│   │   ├── executor.py     # Parallel research execution
│   │   └── publisher.py    # Report synthesis
│   ├── llm/
│   │   ├── gemini_client.py # Gemini API wrapper
│   │   └── prompts.py       # System prompts
│   ├── main.py              # FastAPI application
│   ├── graph.py             # LangGraph workflow
│   ├── models.py            # Pydantic models
│   ├── memory.py            # In-memory storage
│   └── requirements.txt
│
└── frontend/
    ├── src/
    │   ├── api/
    │   │   ├── client.ts    # API client
    │   │   └── hooks.ts     # React Query hooks
    │   ├── components/
    │   │   ├── ProgressTracker.tsx
    │   │   └── ReportDisplay.tsx
    │   ├── pages/
    │   │   └── QueryPage.tsx
    │   ├── App.tsx
    │   └── main.tsx
    ├── package.json
    └── vite.config.ts
```

## 🎯 Workflow Details

### 1. Planner Agent
- Analyzes user query
- Generates 6-10 focused sub-questions
- Covers: background, current state, findings, methodologies, controversies, limitations, future directions

### 2. Executor Agents (Parallel)
- Each sub-question is researched independently
- Simulates web search and retrieval
- Extracts facts, summaries, and citations
- Returns structured data with sources

### 3. Publisher Agent
- Synthesizes all research into cohesive narrative
- Creates structured report with sections:
  - Introduction
  - Background & Fundamentals
  - Current Evidence & Findings
  - Methodologies & Approaches
  - Controversies & Limitations
  - Future Directions & Implications
  - Conclusion
  - References
- Uses inline citations [S1], [S2], etc.
- Ensures 2000+ word count

## ⚙️ Configuration

### Backend Environment Variables
Create a `.env` file in the `backend/` directory:
```env
GEMINI_API_KEY=your_api_key_here
```

### Frontend Environment Variables (Optional)
Create a `.env` file in the `frontend/` directory:
```env
VITE_API_URL=http://localhost:8000
```

## 🔒 Important Notes

- **In-Memory Only**: All data is stored in memory and will be lost on server restart
- **No Persistence**: This is by design - no database or file storage
- **Demo Purposes**: The executor currently simulates web search. For production, integrate real search APIs
- **API Costs**: Be aware of Gemini API usage and rate limits

## 🛠️ Development

### Backend Development
```bash
cd backend
uvicorn main:app --reload
```

### Frontend Development
```bash
cd frontend
npm run dev
```

### Build Frontend for Production
```bash
cd frontend
npm run build
```

## 📝 License

MIT License - feel free to use this project for learning and development.

## 🤝 Contributing

Contributions are welcome! This is a demonstration project showcasing multi-agent research workflows.

## 🐛 Troubleshooting

### Backend won't start
- Ensure Python 3.10+ is installed
- Check that all dependencies are installed: `pip install -r requirements.txt`
- Verify GEMINI_API_KEY is set in `.env`

### Frontend compilation errors
- Run `npm install` to ensure all dependencies are installed
- Clear node_modules and reinstall: `rm -rf node_modules && npm install`

### CORS errors
- Ensure backend is running on port 8000
- Check frontend proxy configuration in `vite.config.ts`

## 📚 Learn More

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Google Gemini API](https://ai.google.dev/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)

---

