# OGCheck — pure stdlib, no dependencies, tiny image.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PORT=8000
WORKDIR /app
COPY ogcheck ./ogcheck
COPY web ./web

# Generate the SEO landing pages + sitemap into web/ at build time.
RUN python -m ogcheck.seo

# Run as non-root.
RUN useradd --system --create-home app && chown -R app:app /app
USER app

EXPOSE 8000
CMD ["python", "-m", "ogcheck.api"]
