# Deployment & HTTPS Guide (Render)

Use this guide to deploy once and get a stable public HTTPS URL for parents.

## 1) What is already prepared in this repo

- `requirements.txt` includes `gunicorn`.
- `render.yaml` is included for one-click Render setup.
- `Procfile` is included for compatibility.

## 2) Deploy on Render (recommended)

1. Push this project to GitHub.
2. Open Render dashboard: `https://dashboard.render.com`
3. Click **New +** → **Blueprint**.
4. Select your GitHub repo.
5. Render detects `render.yaml` automatically.
6. In environment variables, set:
	- `ADMIN_PASS` = your strong admin password
	- (optional) `STUDENT_TOKEN` = token required for student link access
7. Click **Apply** and wait for deployment to finish.

After deployment, you get a URL like:

`https://grades4.onrender.com`

This URL is public and can be opened from any area/network.

## 3) First-run checks

- Open the Render URL and confirm home page loads.
- Open `/admin/login` and verify admin login works with your `ADMIN_PASS`.
- Add/check a student and test result lookup from a phone on mobile data.

## 4) Updating later

- Push new commits to GitHub.
- Render auto-deploys (enabled in `render.yaml`).

## 5) Security notes

- Keep `ADMIN_PASS` strong and private.
- Do not share admin URLs with parents.
- Rotate `SECRET_KEY`/tokens if leaked.
