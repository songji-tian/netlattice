FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NETLATTICE_TOPOLOGY=/app/topology.yaml

WORKDIR /app

COPY console/requirements.txt /app/console/requirements.txt
RUN python -m pip install --no-cache-dir -r /app/console/requirements.txt

COPY console /app/console
COPY scripts /app/scripts
COPY topology.example.yaml /app/topology.yaml

EXPOSE 8787

CMD ["uvicorn", "console.app:app", "--host", "0.0.0.0", "--port", "8787"]
