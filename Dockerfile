FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir ".[test]"
COPY modell ./modell
COPY wissen ./wissen
COPY eval ./eval
COPY tests ./tests
ENV DATENVERZEICHNIS=/app/daten PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
