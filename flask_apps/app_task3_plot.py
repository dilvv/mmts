#!/usr/bin/env python3
''' Deprecated file since I used grafana dashboard building figures. '''
from __future__ import annotations
import os
import re
from flask import Flask, render_template_string, send_from_directory, send_file, url_for, abort, Response, redirect, jsonify
import logging
import sys

log = logging.getLogger(__name__)

from flask import Blueprint
from flask import current_app

app = Blueprint('plot_task3', __name__, url_prefix="/plot_task3")


#app = Flask(__name__)

# --- Configuration ---
# # Base directory where your run1 PNGs live. You can override via env var DAQPLOTS_DIR.
# BASE_PLOTS_DIR = os.environ.get("DAQPLOTS_DIR", os.path.expanduser("~/stored_data/daqplots/"))
# # Default/fallback image when a required figure is missing or fails to load.
# DEFAULT_IMG = os.path.expanduser("~/stored_data/daqplots.nodata.png")

CONF_FILE = 'data/mmts_configurations.yaml'

#andrewCONF = f'{os.environ.get("AndrewModuleTestingGUI_BASE")}/configuration.yaml'
try:
    with open(CONF_FILE, 'r') as fIN:
        import yaml
        conf = yaml.safe_load(fIN)
        BASE_PLOTS_DIR = f'{conf["MMTS_package_path"]["HGCal_Module_Production_Toolkit"]}/out/'
    DEFAULT_IMG = f'{os.environ.get("FLASK_BASE")}/data/daqplots.nodata.png'
except FileNotFoundError as e:
    raise FileNotFoundError(f'\n\n[NoEnvVar] Need to `source ./init_bash_vars.sh` before execute this file') from e

# Blocks/keys to render (3 columns x 1 row)
BLOCKS = [
        "1L", "1C", "1R",
        ]

# Allow only strict file names like "1L-adc_mean.png"
FNAME_RE = re.compile(r"^(?P<key>[1-9][LCR])-.*\.png$")


def has_png(path: str) -> bool:
    try:
        return os.path.isfile(path)
    except OSError:
        return False

@app.route("/plot_version/<path:filepath>")
def plot_version(filepath: str):
    """
    Return mtime-based version for a plot. If missing, return exists=false.
    Frontend uses this to decide whether to refresh the <img>.
    """
    log.debug(f'[RequestedVersion] {filepath}')

    fs_path = os.path.join(BASE_PLOTS_DIR, filepath)

    fileID = os.path.getmtime(fs_path) if has_png(fs_path) else None ### if None, no png file found in syste. So server will returned a default png file.
    return jsonify({'version': fileID})





@app.route("/plots/<path:filepath>")
def serve_plot(filepath: str):
    log.debug(f'[RequestedFilename] {filepath}')

    fs_path = os.path.join(BASE_PLOTS_DIR, filepath)
    log.debug(f'[RequiredFigure] full path "{fs_path}"')

    if has_png(fs_path):
        log.debug(f'sending image {filepath}')
        resp = send_from_directory(BASE_PLOTS_DIR, filepath)
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp

    if has_png(DEFAULT_IMG):
        log.debug(f'sending default image {DEFAULT_IMG}')
        resp = send_file(DEFAULT_IMG)
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp

    svg = f"""
    <svg xmlns='http://www.w3.org/2000/svg' width='800' height='500'>
      <rect width='100%' height='100%' fill='#0b1020'/>
      <text x='50%' y='45%' text-anchor='middle' fill='#9fb0ff' font-size='22' font-family='monospace'>Missing figure</text>
      <text x='50%' y='55%' text-anchor='middle' fill='#9fb0ff' font-size='16' font-family='monospace'>{filepath}</text>
    </svg>
    """
    log.warning('no any file sent!!!')
    return Response(svg, mimetype="image/svg+xml")




@app.route("/gallery/<run>/<key>")
def block_page(run: str, key: str):
    imgs = []
    if run == 'summary':
        for fname in ('summary0_ZoomTemp_IV.png', 'summary1_Minus40_IV.png', 'summary2_Plus20_IV.png'):
            fs_path = os.path.join(BASE_PLOTS_DIR, fname)
            exists = has_png(fs_path)
            src = url_for("plot_task3.serve_plot", filepath=fname)
            imgs.append({"file": fname, "src": src, "exists": exists})

    self_url = url_for("plot_task3.block_page", run=run, key=key)

    template = r"""<!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>IV Curves</title>
      <style>
        html { overflow:hidden; }
        body { background:#121a33; color:#e7ecff; font-family:sans-serif; margin:0; padding:12px; overflow:hidden; }
        .block-title { font-weight:bold; margin-bottom:10px; }
        .block-title{display:flex;justify-content:space-between;align-items:center;margin:2px 2px 10px;padding:8px 10px;background:#0e1530;border:1px solid #2a3a7a66;border-radius:12px}
        .figwrap{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px}
        figure{margin:0;padding:10px;border-radius:12px;background:#0b122a;border:1px solid #2a3a7a55}
        img{width:100%;object-fit:contain;display:block;border-radius:8px;background:#050915}
        figcaption{margin-top:8px;font-size:.85rem;color:var(--muted);word-break:break-all}
      </style>
    </head>
    <body>
      <a href="{{ self_url }}" target="_blank">
        <div class="block-title">IV {{ key }}</div>
      </a>

      <div class="figwrap">
        {% for img in imgs %}
        <figure>
          <img data-fname="{{ img.file }}" src="{{ img.src }}" alt="{{ img.file }}" />
          <figcaption>{{ img.file }}</figcaption>
        </figure>
        {% endfor %}
      </div>

      <script>
        const POLL_MS = 5000;
        const lastVersion = {}; // fname -> version

        async function checkAndUpdateOne(imgEl) {
          const fname = imgEl.dataset.fname;
          const vUrl = "{{ url_for('plot_task3.plot_version', filepath='__F__') }}".replace("__F__", encodeURIComponent(fname));

          try {
            const r = await fetch(vUrl, { cache: "no-store" });
            const info = await r.json();

            // missing -> keep previous figure (do nothing)
            // if (!info.exists || info.version == null) return;

            if (lastVersion[fname] === info.version) return;
            lastVersion[fname] = info.version;

            // cache-bust image only when changed, and only swap if load succeeds
            const baseSrc = imgEl.src.split("?")[0];
            const newSrc = baseSrc + "?v=" + info.version;

            const tmp = new Image();
            tmp.onload = () => { imgEl.src = newSrc; };
            tmp.src = newSrc;

          } catch (e) {
            // network/server issue -> keep current image
            return;
          }
        }

        async function tick() {
          const imgs = document.querySelectorAll("img[data-fname]");
          for (const img of imgs) {
            await checkAndUpdateOne(img);
          }
        }

        tick();
        setInterval(tick, POLL_MS);
      </script>
    </body>
    </html>"""

    return render_template_string(template, run=run, key=key, imgs=imgs, self_url=self_url)


if __name__ == "__main__":
    ''' Deprecated file since I used grafana dashboard building figures. '''
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
       #return redirect( url_for('plot_task3.gallery', run='summary') )
        return redirect( url_for('plot_task3.block_page', run='summary', key='Summary') )

    _app.register_blueprint(app)
    _app.run(host="0.0.0.0", port=5005, debug=True)

    ''' Deprecated file since I used grafana dashboard building figures. '''
