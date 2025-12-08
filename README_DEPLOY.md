# Deploying to Koyeb

1. Build the repo (Dockerfile already in `backend1.0/`).
2. Set env vars in Koyeb: `FLASK_SECRET_KEY`, `SITE_BASE_URL`, and optional `PORT=8080`.
3. Deploy using Koyeb CLI or dashboard using `koyeb.yaml` (which uses the Dockerfile).
4. Use `gunicorn` command already defined in Dockerfile.
