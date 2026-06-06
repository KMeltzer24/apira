# Frontend

React (Vite) web app for local development. It has two screens — login and portfolio view — that talk to the User Service (`:8001`) and Portfolio Service (`:8002`) on `localhost`.

The dev server runs on **port 3000** (set in `vite.config.js`).

## Run

```bash
npm install
npm run dev
```

Then open [http://localhost:3000](http://localhost:3000).

The frontend is not deployed to EC2. For testing the live APIs, use Postman or curl — see the [root README](../README.md).
