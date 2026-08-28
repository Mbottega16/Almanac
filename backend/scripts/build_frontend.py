"""Build the frontend and copy it into backend/static/ so one deployment
(the Vercel Python service) serves both the API and the app.

Run from backend/:  .venv\\Scripts\\python scripts\\build_frontend.py
Requires npm on PATH. The frontend is built with an empty VITE_API_BASE_URL
so it calls /api on the same origin.
"""
import pathlib
import shutil
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
FRONTEND = ROOT / "frontend"
DIST = FRONTEND / "dist"
STATIC = ROOT / "backend" / "static"


def main() -> None:
    env_prod = FRONTEND / ".env.production"
    env_prod.write_text(
        "# Combined single-service deploy: same origin, so no base URL.\n"
        "VITE_API_BASE_URL=\n",
        encoding="utf-8",
    )
    subprocess.run("npm install", cwd=FRONTEND, shell=True, check=True)
    subprocess.run("npm run build", cwd=FRONTEND, shell=True, check=True)
    if STATIC.exists():
        shutil.rmtree(STATIC)
    shutil.copytree(DIST, STATIC)
    print(f"copied {DIST} -> {STATIC}")


if __name__ == "__main__":
    main()
