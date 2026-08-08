FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 ZWORKFORCE_ENV=production ZWORKFORCE_HOST=0.0.0.0 ZWORKFORCE_PORT=9569 ZWORKFORCE_DATA_DIR=/var/lib/zworkforce ZWORKFORCE_WORKSPACE_ROOT=/workspace
WORKDIR /app
RUN useradd --system --uid 10001 --create-home zworkforce && mkdir -p /var/lib/zworkforce /workspace && chown -R zworkforce:zworkforce /var/lib/zworkforce /workspace
COPY --chown=zworkforce:zworkforce zworkforce ./zworkforce
COPY --chown=zworkforce:zworkforce pyproject.toml README.md LICENSE ./
USER zworkforce
EXPOSE 9569
VOLUME ["/var/lib/zworkforce","/workspace"]
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9569/health',timeout=2).read()" || exit 1
CMD ["python","-m","zworkforce","serve"]
