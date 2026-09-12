"""
Tkinter -> APK Converter (Flask app)
Author: Chintan Parmar

Upload a Tkinter (.py) script. The app:
  1. Runs it through an AST-based converter (converter.py) that rewrites
     common Tkinter widgets into their closest Kivy equivalents.
  2. Generates a buildozer.spec for the converted project.
  3. Tries to build a real .apk with `buildozer android debug`, if
     buildozer + the Android SDK/NDK are available on this machine.
  4. If the Android build toolchain isn't installed (it's a multi-GB
     download of Google's SDK/NDK), falls back to packaging the
     converted, ready-to-build Kivy project as a .zip so the user can
     build the APK themselves with one command.

Honest limitation: Tkinter itself has no Android runtime. This tool does
NOT magically run arbitrary Tkinter code on a phone -- it converts what it
can to Kivy (which DOES run on Android) and clearly flags what it can't.
"""

import os
import shutil
import subprocess
import uuid
import zipfile
from pathlib import Path

from flask import Flask, render_template, request, send_file, flash, redirect, url_for

from converter import convert_source
from spec_template import generate_spec

APP_AUTHOR = "Chintan Parmar"

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
BUILD_DIR = BASE_DIR / "builds"
UPLOAD_DIR.mkdir(exist_ok=True)
BUILD_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".py"}
MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB, plenty for a single script

app = Flask(__name__)
app.secret_key = "tk2apk-secret-key-change-me"
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH


def buildozer_available() -> bool:
    """Check whether buildozer AND a usable Android toolchain are present."""
    return shutil.which("buildozer") is not None


def build_apk(project_dir: Path) -> Path | None:
    """
    Attempts to build the APK with buildozer. Returns the path to the
    built .apk on success, or None if the build fails / tooling is missing.
    This can take 10-40+ minutes on first run (SDK/NDK download + compile).
    """
    if not buildozer_available():
        return None

    try:
        subprocess.run(
            ["buildozer", "-v", "android", "debug"],
            cwd=str(project_dir),
            check=True,
            timeout=3600,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return None

    bin_dir = project_dir / "bin"
    if bin_dir.exists():
        apks = list(bin_dir.glob("*.apk"))
        if apks:
            return apks[0]
    return None


def package_as_zip(project_dir: Path, zip_path: Path) -> Path:
    """Fallback: zip the converted, buildozer-ready project for the user."""
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in project_dir.rglob("*"):
            if file.is_file():
                zf.write(file, file.relative_to(project_dir))
    return zip_path


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", author=APP_AUTHOR)


@app.route("/convert", methods=["POST"])
def convert():
    uploaded_file = request.files.get("tkinter_file")
    app_title = request.form.get("app_title", "").strip() or "Converted App"

    if not uploaded_file or uploaded_file.filename == "":
        flash("Please choose a Python (.py) file to upload.")
        return redirect(url_for("index"))

    ext = Path(uploaded_file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        flash("Only .py files are supported.")
        return redirect(url_for("index"))

    job_id = uuid.uuid4().hex[:10]
    job_dir = BUILD_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    original_path = job_dir / "original.py"
    uploaded_file.save(original_path)
    source_code = original_path.read_text(encoding="utf-8", errors="ignore")

    # --- Convert Tkinter -> Kivy ---
    kivy_source, report = convert_source(source_code)
    (job_dir / "main.py").write_text(kivy_source, encoding="utf-8")

    # --- Generate buildozer.spec ---
    spec_text = generate_spec(title=app_title, package_name=app_title.replace(" ", "_"))
    (job_dir / "buildozer.spec").write_text(spec_text, encoding="utf-8")

    # --- Add a build helper script + README for the user's own machine ---
    (job_dir / "build_apk.sh").write_text(
        "#!/usr/bin/env bash\n"
        "# Run this on a Linux machine (or WSL) with buildozer installed.\n"
        "# First-time setup: pip install buildozer cython\n"
        "# Requires ~2-4 GB of Android SDK/NDK downloads on first run.\n"
        "buildozer -v android debug\n",
        encoding="utf-8",
    )
    (job_dir / "README.md").write_text(
        f"# {app_title}\n\n"
        f"Converted from a Tkinter script by tk2apk. Author: {APP_AUTHOR}\n\n"
        "## Conversion notes\n" +
        ("\n".join(f"- {w}" for w in report.warnings) or "- No warnings.") + "\n\n"
        "## Widgets converted\n" +
        ("\n".join(f"- {w}" for w in report.converted_widgets) or "- None detected.") + "\n\n"
        "## Needs manual attention\n" +
        ("\n".join(f"- {w}" for w in report.unsupported) or "- None.") + "\n\n"
        "## How to build the APK yourself\n"
        "1. Install buildozer on Linux/macOS/WSL: `pip install buildozer cython`\n"
        "2. Install Android build deps (Java 17, git, unzip, autoconf, etc.)\n"
        "3. From this folder, run: `bash build_apk.sh`\n"
        "4. First build downloads the Android SDK/NDK (~2-4 GB) and can take "
        "20-40+ minutes. The .apk will appear in the `bin/` folder.\n",
        encoding="utf-8",
    )

    # --- Try to actually build the APK on this server ---
    apk_path = build_apk(job_dir)

    if apk_path:
        final_apk = BUILD_DIR / f"{job_id}.apk"
        shutil.copy(apk_path, final_apk)
        return render_template(
            "result.html",
            author=APP_AUTHOR,
            built=True,
            download_name=f"{job_id}.apk",
            warnings=report.warnings,
            converted=report.converted_widgets,
            unsupported=report.unsupported,
        )

    # --- Fallback: give the user the converted, ready-to-build project ---
    zip_path = BUILD_DIR / f"{job_id}.zip"
    package_as_zip(job_dir, zip_path)
    return render_template(
        "result.html",
        author=APP_AUTHOR,
        built=False,
        download_name=f"{job_id}.zip",
        warnings=report.warnings,
        converted=report.converted_widgets,
        unsupported=report.unsupported,
    )


@app.route("/download/<name>")
def download(name):
    path = BUILD_DIR / name
    if not path.exists():
        flash("That file no longer exists.")
        return redirect(url_for("index"))
    return send_file(path, as_attachment=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
