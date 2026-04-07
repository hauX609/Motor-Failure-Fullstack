# Motor Failure Frontend

React + TypeScript + Vite dashboard for the Motor Failure platform.

## Scripts
- `npm run dev` - start development server
- `npm run build` - production build
- `npm run preview` - preview production build

## Local Setup
```bash
cp .env.example .env.development
npm install
npm run dev
```

## Required Environment Variables
- `VITE_API_BASE_URL` - backend API base URL
- `VITE_APP_ENV` - `development` or `production`
- `VITE_USE_MOCK_DATA` - `true` or `false`
- `VITE_ALLOW_MOCK_IN_PROD` - keep `false` for production

For full stack setup, see the root `README.md`.

