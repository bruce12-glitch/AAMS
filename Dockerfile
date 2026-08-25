# ---- Builder: compile native wheels (insightface needs a C toolchain) ----
FROM python:3.11-slim AS builder

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY fablab-face-attendance/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---- Runtime ----
FROM python:3.11-slim

# libgl1/libglib2.0: required by cv2 at import time
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

COPY --from=builder /install /usr/local
COPY fablab-face-attendance/ .

# Runtime data lives on volumes (see docker-compose.yml):
#   database/  images/  models/
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
