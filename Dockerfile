# Hit By A Bus Plan - Dockerfile
# Self-hostable emergency plan with live editing

FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies (pandoc and texlive for PDF)
RUN apt-get update && apt-get install -y \
    curl \
    pandoc \
    texlive-latex-base \
    texlive-fonts-recommended \
    texlive-latex-extra \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies for MkDocs and Editor
RUN pip install --no-cache-dir \
    mkdocs-material==9.5.6 \
    fastapi==0.104.1 \
    uvicorn[standard]==0.24.0 \
    jinja2==3.1.2 \
    python-multipart==0.0.6 \
    pyyaml==6.0.1 \
    watchdog==3.0.0 \
    aiofiles==23.2.1 \
    detect-secrets==1.4.0

# Create app user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy only application code (not user content)
COPY editor/ /app/editor/
COPY scripts/ /app/scripts/

# Copy default/template files
COPY site/ /app/site-template/
COPY content/ /app/content-template/

# Create directories for volumes and set permissions
RUN mkdir -p /app/content /app/site /app/output /app/data && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose ports for both services
EXPOSE 8000 8001

# Environment variables
ENV MKDOCS_HOST=0.0.0.0
ENV MKDOCS_PORT=8000
ENV EDITOR_HOST=0.0.0.0
ENV EDITOR_PORT=8001
ENV ENABLE_EDITOR=false
ENV REQUIRE_PERSONALISATION=true

# Health check for main site
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/ || exit 1

# Default working directory
WORKDIR /app

# Startup scripts that can run in different modes
COPY scripts/docker-entrypoint.sh /app/scripts/
COPY scripts/init-user-content.sh /app/scripts/
USER root
RUN chmod +x /app/scripts/docker-entrypoint.sh /app/scripts/init-user-content.sh
USER appuser

# Default command
CMD ["/app/scripts/docker-entrypoint.sh"]

# Build metadata
LABEL maintainer="your-email@example.com"
LABEL description="Hit By A Bus Plan - Emergency information with live editing"
LABEL version="2.0.0"
LABEL org.opencontainers.image.source="https://github.com/yourusername/hit-by-a-bus"
