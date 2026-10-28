# ScholarSynth Frontend

React + TypeScript frontend for the ScholarSynth research system.

## Setup

1. Install dependencies:
```bash
npm install
```

2. Start development server:
```bash
npm run dev
```

Frontend runs at http://localhost:3000

## Build for Production

```bash
npm run build
npm run preview  # Preview production build
```

## Features

- **Query Input**: Research question submission
- **Real-time Progress**: Live updates during research
- **Report Display**: Markdown-rendered final report
- **Download/Copy**: Export reports as Markdown

## Tech Stack

- React 18
- TypeScript
- Vite
- Tailwind CSS
- React Query
- Axios
- Lucide React (icons)
- React Markdown

## Development

The app uses Vite's proxy to forward `/api/*` requests to the backend at `http://localhost:8000`.

Make sure the backend is running before starting the frontend.
