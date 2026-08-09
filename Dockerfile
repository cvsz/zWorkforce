FROM python:3.13-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY zworkforce ./zworkforce
RUN python -m pip install --no-cache-dir . \
    && groupadd --system --gid 10001 zworkforce \
    && useradd --system --uid 10001 --gid zworkforce --home /nonexistent --shell /usr/sbin/nologin zworkforce \
    && mkdir -p /data /workspace \
    && chown -R zworkforce:zworkforce /data /workspace /app
USER 10001:10001
ENV ZWORKFORCE_DATA_DIR=/data ZWORKFORCE_WORKSPACE_ROOT=/workspace ZWORKFORCE_HOST=0.0.0.0 ZWORKFORCE_PORT=9569
EXPOSE 9569
VOLUME ["/data", "/workspace"]
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 CMD ["python","-c","import json,urllib.request; assert json.load(urllib.request.urlopen('http://127.0.0.1:9569/health',timeout=3))['status']=='ok'"]
ENTRYPOINT ["zworkforce"]
CMD ["serve"]
