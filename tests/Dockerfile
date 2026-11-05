FROM python:3.13-slim-bookworm@sha256:281d39ff02e3b389401586134ff9e6572954687822a58055ec07a60ded4e0b7f
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /opt/minishop
COPY requirements.txt ./requirements.txt
COPY tests/requirements.txt ./tests/requirements.txt
RUN pip install --no-cache-dir -r tests/requirements.txt \
    && groupadd --gid 10001 minishop \
    && useradd --uid 10001 --gid 10001 --no-create-home minishop
COPY tests ./tests
COPY scripts ./scripts
USER 10001:10001
CMD ["python", "-m", "pytest", "tests", "-v", "-rA", "-p", "no:cacheprovider", "--junitxml=/results/junit.xml"]
