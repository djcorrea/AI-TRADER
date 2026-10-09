FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HOST=0.0.0.0 STATE_DIR=/state OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 ALLOW_REMOTE_CONTROL=0
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
COPY requirements-lock.txt .
RUN pip install --no-cache-dir -r requirements-lock.txt
COPY . .
CMD ["python", "run.py", "cloud"]
