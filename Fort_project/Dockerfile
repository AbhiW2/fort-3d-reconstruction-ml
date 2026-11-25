# FROM python:3.11-slim

# ENV PYTHONPATH=/app \
#     PYTHONUNBUFFERED=1 \
#     PYTHONDONTWRITEBYTECODE=1 \
#     HF_HOME=/home/app/.cache/huggingface

# WORKDIR /app

# RUN apt-get update \
#     && apt-get install --no-install-recommends -y libgl1 libglib2.0-0 \
#     && rm -rf /var/lib/apt/lists/* \
#     && useradd --create-home --uid 10001 app

# COPY requirements-api.txt /app/requirements.txt
# RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch torchvision \
#     && pip install --no-cache-dir -r /app/requirements.txt

# COPY . /app/Fort_project
# RUN chown -R app:app /app

# USER app

# EXPOSE 8000

# CMD ["python", "-m", "uvicorn", "Fort_project.app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]



FROM python:3.11-slim

ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/home/app/.cache/huggingface

WORKDIR /app

RUN apt-get update \
    && apt-get install --no-install-recommends -y libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 app

COPY requirements-api.txt /app/requirements.txt
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch torchvision \
    && pip install --no-cache-dir -r /app/requirements.txt

# NEW: download the embedding model at build time
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

COPY . /app/Fort_project
RUN chown -R app:app /app /home/app

USER app
ENV HF_HUB_OFFLINE=1

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "Fort_project.app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]