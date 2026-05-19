FROM cgr.dev/chainguard/python:latest-dev@sha256:33289f14dabce99c0a48744abfa09d417278da1eeb5e028f37977792c51b826f

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --user --require-hashes -r requirements.txt

ENV PATH="/home/nonroot/.local/bin:${PATH}"
ENV PYTHONPATH=/app

COPY requirements.in ./
COPY .claude-plugin/ ./.claude-plugin/
COPY .github/ ./.github/
COPY plugins/ ./plugins/
COPY tests/ ./tests/

ENTRYPOINT ["python", "-m", "pytest", "tests/", "-v", "--cov=tests", "--cov-report=term-missing"]
