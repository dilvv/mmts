# --- Base: conda-forge Miniforge (works well for conda-forge packages) ---
FROM condaforge/miniforge3:24.7.1-0

SHELL ["/bin/bash", "-lc"]

# --- System deps (serial, build tools, git, etc.) ---
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    bash \
    ca-certificates \
    curl \
    wget \
    build-essential \
    pkg-config \
    libusb-1.0-0 \
    udev \
    && rm -rf /var/lib/apt/lists/*

# --- Create conda env (python 3.9 matches your README recommendation) ---
ENV ENVNAME=mmts
RUN mamba create -y -n ${ENVNAME} python=3.9 && mamba clean -a -y

# --- Copy repo into container ---
WORKDIR /app
COPY . /app

# --- Install Python deps (conda first) ---
RUN mamba install -y -n ${ENVNAME} -c conda-forge \
    flask \
    flask-socketio \
    requests \
    sphinx \
    paramiko \
    pyvisa \
    pyvisa-py \
    pyyaml \
    flask-wtf \
    myst-parser \
    flask-cors \
    pymeasure \
    psycopg \
    && mamba clean -a -y

# Optional: some Flask-SocketIO deployments prefer eventlet
RUN mamba run -n ${ENVNAME} pip install --no-cache-dir eventlet

ENV PYTHONPATH=/app
ENV LOG_LEVEL=INFO
ENV BASH_SCRIPT_FOLDER=/app/scripts/task2_pedestalrun/
ENV FLASK_BASE=/app
ENV LOG_LEVEL=DEBUG
ENV AndrewModuleTestingGUI_BASE=/app/external_packages/hgcal-module-testing-gui



EXPOSE 5001

# --- Start the app ---
CMD ["bash", "-lc", "ls ; exec mamba run -n mmts python3 app.py"]
