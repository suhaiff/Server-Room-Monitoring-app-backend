FROM python:3.12-alpine
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY api.py simulate_hardware.py ./
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8010"]
