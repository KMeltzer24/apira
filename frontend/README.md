# Frontend

React (Vite) web app for the Apira project. It has two screens — a fake login and a portfolio view — that talk to the User Service (`:8001`) and Portfolio Service (`:8002`).

The dev server runs on **port 3000** (set in `vite.config.js`).

## Run

```bash
npm install
npm run dev
```

Then open [http://localhost:3000](http://localhost:3000).

For running the whole stack (frontend + both services) together with Docker, see the [root README](../README.md).
