FROM python:3.13-slim-bookworm@sha256:281d39ff02e3b389401586134ff9e6572954687822a58055ec07a60ded4e0b7f
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /opt/minishop
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt \
    && groupadd --gid 10001 minishop \
    && useradd --uid 10001 --gid 10001 --no-create-home minishop
COPY services/common ./common
COPY services/catalog/app ./app
USER 10001:10001
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "30", "--worker-tmp-dir", "/tmp", "--error-logfile", "-", "app:create_app()"]
