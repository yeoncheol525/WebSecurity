FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY . .
# A local wheelhouse is optional for the isolated Ubuntu VM.
RUN if [ -d wheelhouse ]; then \
      python -m pip install --no-cache-dir --no-index --find-links=wheelhouse -r requirements.txt && rm -rf wheelhouse; \
    else \
      python -m pip install --no-cache-dir -r requirements.txt; \
    fi

EXPOSE 5000
CMD ["python", "run.py", "--host", "0.0.0.0", "--port", "5000"]
