# Career Compass — Frontend

React 19 + TypeScript + Vite single-page UI for uploading a CV and viewing the parsed profile returned by the backend.

## Prerequisites

- Node.js 20+ (or any version supported by the Vite release in `package.json`)
- The backend running on `http://localhost:8000` (see the project root `README.md`)

## Setup

```powershell
cd frontend
npm install
```

## Development

```powershell
npm run dev
```

The dev server listens on `http://localhost:5173`. CORS is already configured on the backend for this origin.

## Build

```powershell
npm run build
npm run preview
```
