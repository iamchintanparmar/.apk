# Tkinter → APK Converter

**Author: Chintan Parmar**

A Flask web app that takes a Tkinter (`.py`) script, auto-converts what it can
into an equivalent [Kivy](https://kivy.org) app (the closest Android-capable
GUI framework), and tries to build a real `.apk` using
[Buildozer](https://buildozer.readthedocs.io/).

## Important: read this before you rely on it

Tkinter itself **cannot run on Android** — there is no Tcl/Tk build for the
platform, and no tool (including this one) can change that. What this app
does instead:

1. Parses your Tkinter script's AST.
2. Rewrites recognizable, common patterns into Kivy equivalents:
   - `tk.Label`, `tk.Button`, `tk.Entry`, `tk.Frame`, `tk.Checkbutton`, `tk.Text`
   - `.config(text=...)`, `command=callback`
   - Your own helper functions/business logic are carried over unchanged,
     since that part of your code is UI-framework independent.
3. Anything it can't confidently translate is left in place and marked with
   `# TODO: manual conversion needed` — never silently dropped or guessed at.
4. Generates a ready-to-build `buildozer.spec` + project folder.
5. If this server has `buildozer` + the Android SDK/NDK installed, it builds
   the APK directly and gives you a download link.
6. **Otherwise** (the common case — the SDK/NDK is a 2-4 GB download and
   isn't something you'd normally install on a small web server), it zips up
   the converted, ready-to-build project so you can compile the APK yourself
   with one command on your own machine.

Complex or highly custom Tkinter UIs (custom canvas drawing, `ttk` themed
widgets, multi-window `Toplevel` flows, drag-and-drop, etc.) will need some
manual porting after the automatic pass — the conversion notes on the
results page tell you exactly what was and wasn't handled.

## Project structure

```
tk2apk/
├── app.py              # Flask routes: upload, convert, build, download
├── converter.py        # AST-based Tkinter -> Kivy translator
├── spec_template.py     # Generates buildozer.spec
├── requirements.txt
├── templates/
│   ├── index.html
│   └── result.html
├── static/
│   └── style.css
├── uploads/             # uploaded scripts (created at runtime)
└── builds/               # converted projects + built APKs/zips (runtime)
```

## Running it locally

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open http://localhost:5000, upload a Tkinter `.py` file, give your app a
name, and click **Convert to APK**.

## Enabling real on-server APK builds (optional)

By default, most machines won't have the Android toolchain installed, so
the app will fall back to giving you a downloadable, ready-to-build project.
To let the *server itself* compile APKs:

```bash
pip install buildozer cython
# Linux build dependencies (Debian/Ubuntu example):
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf \
    libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev \
    libtinfo5 cmake libffi-dev libssl-dev
```

The first build downloads the Android SDK/NDK (~2-4 GB) and can take
20-40+ minutes; subsequent builds are much faster.

## Building the APK yourself from the downloaded project

If you get a `.zip` instead of a `.apk`, unzip it and run:

```bash
pip install buildozer cython
bash build_apk.sh
```

The finished `.apk` will appear in the project's `bin/` folder.

## Limitations, honestly stated

- Only a common subset of Tkinter widgets/patterns is auto-converted.
- `ttk` themed widgets, `Canvas` drawing, `Toplevel` multi-window apps, and
  drag-and-drop are not auto-converted — they're flagged for manual work.
- Actual APK compilation requires the Android SDK/NDK, which this tool does
  not bundle (it's multiple gigabytes and platform-specific).
- This is a best-effort developer tool, not a guarantee that any arbitrary
  Tkinter app becomes a polished Android app with zero manual work.
