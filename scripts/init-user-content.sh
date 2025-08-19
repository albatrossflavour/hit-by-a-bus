#!/bin/bash
# Hit By A Bus Plan - Initialize user content from templates
set -e

echo "🚀 Initializing Hit By A Bus Plan..."

# Create directories if they don't exist
mkdir -p /app/content /app/site /app/output

# Copy templates if user content doesn't exist
if [ ! -f "/app/content/index.md" ]; then
    echo "📋 No user content found, copying templates..."
    cp -r /app/content-template/* /app/content/
    echo "✅ Content templates copied to /app/content/"
fi

if [ ! -f "/app/site/mkdocs.yml" ]; then
    echo "📋 No site config found, copying template..."
    cp -r /app/site-template/* /app/site/
    echo "✅ Site templates copied to /app/site/"
fi

# No config.yml needed - all configuration is in environment variables

# Set proper permissions for the app user
chown -R appuser:appuser /app/content /app/site /app/output /app/data 2>/dev/null || true

echo "✅ Initialization complete!"
