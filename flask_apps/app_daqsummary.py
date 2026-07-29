#!/usr/bin/env python3
from __future__ import annotations
import os
import re
from flask import Flask, render_template_string, send_from_directory, send_file, url_for, abort, Response, redirect
import logging
import sys

log = logging.getLogger(__name__)

from flask import Blueprint
from flask import current_app

app = Blueprint('daqsummary', __name__, url_prefix="/daqsummary")


#app = Flask(__name__)

# --- Configuration ---
# # Base directory where your run1 PNGs live. You can override via env var DAQPLOTS_DIR.
# BASE_PLOTS_DIR = os.environ.get("DAQPLOTS_DIR", os.path.expanduser("~/stored_data/daqplots/"))
# # Default/fallback image when a required figure is missing or fails to load.
# DEFAULT_IMG = os.path.expanduser("~/stored_data/daqplots.nodata.png")
andrewCONF = f'{os.environ.get("AndrewModuleTestingGUI_BASE")}/configuration.yaml'
try:
    with open(andrewCONF, 'r') as fIN:
        import yaml
        conf = yaml.safe_load(fIN)
        BASE_PLOTS_DIR = f'{conf["DataLoc"]}/daqplots/'
        DEFAULT_IMG = f'{conf["DataLoc"]}/daqplots.nodata.png'
except FileNotFoundError as e:
    raise FileNotFoundError(f'\n\n[NoEnvVar] Need to `source ./init_bash_vars.sh` before execute this file') from e

# Blocks/keys to render (3 columns x 2 rows)
BLOCKS = [
        "1L", "1C", "1R",
        "2L", "2C", "2R",
        ]

# Allow only strict file names like "1L-adc_mean.png"
FNAME_RE = re.compile(r"^(?P<key>[1-9][LCR])-.*\.png$")


def has_png(path: str) -> bool:
    try:
        return os.path.isfile(path)
    except OSError:
        return False
# ---------------- Template (inline for single-file app) ----------------
### TEMPLATE = r"""<!doctype html>
### <html lang="en">
### <head>
###   <meta charset="utf-8">
###   <meta name="viewport" content="width=device-width, initial-scale=1">
###   <title>DAQ Run1 Plots</title>
###   <style>
###     :root { --bg:#0b1020; --card:#121a33; --ink:#e7ecff; --muted:#9fb0ffb3; }
###     *{box-sizing:border-box}
###     body{margin:0;background:linear-gradient(180deg,#0b1020 0%,#0b1020 60%,#0e1530 100%);color:var(--ink);font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial}
###     header{max-width:2000px;margin:0 auto;padding:24px 20px 8px}
###     h1{margin:0 0 6px}
###     .sub{color:var(--muted);font-size:.95rem}
###     .grid{max-width:2000px;margin:16px auto 60px;padding:0 20px;display:grid;grid-template-columns:repeat(3,1fr);gap:18px}
###     @media (max-width:1100px){.grid{grid-template-columns:repeat(2,1fr)}}
###     @media (max-width:720px){.grid{grid-template-columns:1fr}}
###     .block{background:radial-gradient(120% 120% at 100% 0%,#1a244a 0%,#0f1836 50%,var(--card) 100%);border-radius:16px;border:1px solid #2a3a7a55;box-shadow:0 10px 30px #000a; padding:14px}
###     .block-title{display:flex;justify-content:space-between;align-items:center;margin:2px 2px 10px;padding:8px 10px;background:#0e1530;border:1px solid #2a3a7a66;border-radius:12px}
###     .figwrap{display:grid;grid-template-columns:1fr 1fr;gap:10px}
###     @media (max-width:560px){.figwrap{grid-template-columns:1fr}}
###     figure{margin:0;padding:10px;border-radius:12px;background:#0b122a;border:1px solid #2a3a7a55}
###     img{width:100%;height:260px;object-fit:contain;display:block;border-radius:8px;background:#050915}
###     figcaption{margin-top:8px;font-size:.85rem;color:var(--muted);word-break:break-all}
###     .badge{font-size:.75rem;color:var(--muted)}
###     .legend{max-width:2000px;margin:0 auto 28px;padding:0 20px;color:var(--muted);font-size:.9rem}
###     code{background:#0e1530;border:1px solid #2a3a7a55;padding:2px 6px;border-radius:6px}
###   </style>
### </head>
### """
TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>DAQ Summary</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='css/theme.css') }}">
</head>
<body>
  <header>
    <h1>DAQ Run1 Figures</h1>
    <div class="sub">3 columns × 2 rows. Each block shows <code>_1.png</code> and <code>_2.png</code>. Filenames are captions. Missing images fall back to <code>~/stored_data/daqplots.default.png</code>.</div>
  </header>
  <main class="grid">
    {% for card in cards %}
      <section class="block">
        <div class="block-title"><span>{{ card.title }}</span><span class="badge">run1</span></div>
        <div class="figwrap">
          {% for img in card.images %}
            <figure>
              <img src="{{ img.src }}" alt="{{ img.file }}" loading="lazy">
              <figcaption>{{ img.file }}</figcaption>
            </figure>
          {% endfor %}
        </div>
      </section>
    {% endfor %}
  </main>
  <div class="legend">Serve directory is handled on the server. You can change it via env <code>DAQPLOTS_DIR</code> or by editing <code>BASE_PLOTS_DIR</code> in the app.</div>
</body>
</html>"""







@app.route("/plots/<path:filepath>")
def serve_plot(filepath: str):
    """Serve a plot from BASE_PLOTS_DIR if present, otherwise serve DEFAULT_IMG.
    This keeps all basePath logic in Python so you can add auth, logging, etc.
    """
    # Security: only allow our strict pattern and no path segments
    log.warning(f'[GotFilename] {filepath}')

    if "/" not in filepath or "\\" in filepath or ";" in filepath:
        log.warning(f'[InvalidFilePath] path "{filepath}" should be run1/1L-adc_mean.png')
        abort(404)

    filename = filepath.split('/')[-1]
    if not FNAME_RE.match(filename): ## check filename in formatted. ex: 1L-adc_mean.png
        log.debug(f'[check] FNAME_RE.match(filename) {not FNAME_RE.match(filename.strip())}')
        log.debug(f'abort serve_plot')
        log.warning(f'[InvalidFileName] filename "{filename}" is invalid.')
        abort(404)

    fs_path = os.path.join(BASE_PLOTS_DIR, filepath)
    log.debug(f'[RequiredFigure] full path "{fs_path}"')
    if has_png(fs_path):
        log.debug(f'sending image {filepath}')
        return send_from_directory(BASE_PLOTS_DIR, filepath)

    # Fallback: default image
    if has_png(DEFAULT_IMG):
        log.debug(f'sending default image {DEFAULT_IMG}')
        return send_file(DEFAULT_IMG)

    # Last-resort vector placeholder if DEFAULT_IMG is missing
    svg = f"""
    <svg xmlns='http://www.w3.org/2000/svg' width='800' height='500'>
      <rect width='100%' height='100%' fill='#0b1020'/>
      <text x='50%' y='45%' text-anchor='middle' fill='#9fb0ff' font-size='22' font-family='monospace'>Missing figure</text>
      <text x='50%' y='55%' text-anchor='middle' fill='#9fb0ff' font-size='16' font-family='monospace'>{{{filepath}}}</text>
    </svg>
    """.replace("{{{filepath}}}", filepath)
    log.warning(f'no any file sent!!!')
    return Response(svg, mimetype="image/svg+xml")


@app.route("/gallery/<run>")
def gallery(run: str):
    """Main gallery page—embeds each block page via iframe."""
    cards = []
    for key in BLOCKS:
        url = url_for("daqsummary.block_page", run=run, key=key)
        cards.append({"title": key, "url": url})

    template = r"""<!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>DAQ {{run}} Plots</title>
      <style>
        body { background:#0b1020; color:#e7ecff; font-family:sans-serif; margin:0; }
        h1 { padding:20px; margin:0; }
        .grid { display:grid; grid-template-columns:repeat(3,1fr); gap:16px; padding:20px; max-width:1500px; margin:auto; }
        iframe { width:100%; height:270px; border:none; border-radius:12px; background:#121a33; }
      </style>
    </head>
    <body>
      <h1>DAQ {{run}} Figures</h1>
      <div class="grid">
        {% for card in cards %}
          <iframe src="{{ card.url }}"></iframe>
        {% endfor %}
      </div>
    </body>
    </html>"""
    return render_template_string(template, cards=cards, run=run)


@app.route("/gallery/<run>/<key>")
def block_page(run: str, key: str):
    """Render a page for a single block, showing its two plots."""
    imgs = []
    for i in ("adc_mean", "adc_stdd"):
        fname = f"{run}/{key}-{i}.png"
        fs_path = os.path.join(BASE_PLOTS_DIR, fname)
        exists = has_png(fs_path)
        src = url_for("daqsummary.serve_plot", filepath=fname)
        imgs.append({"file": fname, "src": src, "exists": exists})
    self_url = url_for("daqsummary.block_page", run=run, key=key)

    template = r"""<!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>{{ key }} Plots</title>
      <style>
        html { overflow:hidden; }
        body { background:#121a33; color:#e7ecff; font-family:sans-serif; margin:0; padding:12px; overflow:hidden; }
        .block-title { font-weight:bold; margin-bottom:10px; }
        .block-title{display:flex;justify-content:space-between;align-items:center;margin:2px 2px 10px;padding:8px 10px;background:#0e1530;border:1px solid #2a3a7a66;border-radius:12px}
        .figwrap{display:grid;grid-template-columns:1fr 1fr;gap:10px}
        figure{margin:0;padding:10px;border-radius:12px;background:#0b122a;border:1px solid #2a3a7a55}
        img{width:100%;object-fit:contain;display:block;border-radius:8px;background:#050915}
        figcaption{margin-top:8px;font-size:.85rem;color:var(--muted);word-break:break-all}
      </style>
    </head>
    <body>
      <a href="{{ self_url }}" target="_blank">
        <div class="block-title">Module{{ key }}</div>
      </a>
      <div class="figwrap">
        {% for img in imgs %}
        <figure>
          <img src="{{ img.src }}" alt="{{ img.file }}" />
          <figcaption>{{ img.file }}</figcaption>
        </figure>
        {% endfor %}
      </div>
    </body>
    </html>"""
    return render_template_string(template, run=run, key=key, imgs=imgs)


if __name__ == "__main__":
    import os
    loglevel = os.environ.get('LOG_LEVEL', 'INFO') # DEBUG, INFO, WARNING
    DEBUG_MODE = True if loglevel == 'DEBUG' else False
    logLEVEL = getattr(logging, loglevel)
    logging.basicConfig(stream=sys.stdout,level=logLEVEL,
            format='[basicCONFIG] %(levelname)s - %(message)s',
            datefmt='%H:%M:%S')


    # create a simple flask server for testing
    _app = Flask(__name__)

    @_app.route('/')
    @_app.route('/index')
    def index():
        return redirect( url_for('daqsummary.gallery', run='testrun') )

    _app.register_blueprint(app)
    _app.run(host="0.0.0.0", port=5001, debug=True)

