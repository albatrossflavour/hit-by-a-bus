#!/bin/bash
# Hit By A Bus Plan - Docker Entrypoint
# Supports multiple modes: production, development with editing

set -e

echo "🚌 Hit By A Bus Plan - Starting Container"
echo "========================================"

# Initialize user content if needed
/app/scripts/init-user-content.sh

# Configuration from environment variables
ENABLE_EDITOR=${ENABLE_EDITOR:-false}
REQUIRE_PERSONALISATION=${REQUIRE_PERSONALISATION:-true}
PERSON_NAME=${PERSON_NAME:-}
MKDOCS_HOST=${MKDOCS_HOST:-0.0.0.0}
MKDOCS_PORT=${MKDOCS_PORT:-8000}
EDITOR_HOST=${EDITOR_HOST:-0.0.0.0}
EDITOR_PORT=${EDITOR_PORT:-8001}

# Apply configuration if we have environment variables
if [ -n "$PERSON_NAME" ] && [ "$PERSON_NAME" != "Your Name Here" ] && [ "$PERSON_NAME" != "Your Name" ]; then
    echo "🔧 Applying personalisation from environment variables..."

    # Set defaults for missing environment variables
    PERSON_PRONOUNS=${PERSON_PRONOUNS:-"they/them"}
    PERSON_RELATIONSHIP=${PERSON_RELATIONSHIP:-"me"}
    PLAN_TITLE=${PLAN_TITLE:-"$PERSON_NAME's Emergency Plan"}
    PLAN_SUBTITLE=${PLAN_SUBTITLE:-"Emergency Information Guide"}

    # Create working copy of content (don't modify mounted volumes)
    echo "📁 Creating working copy of content..."
    rm -rf /app/content-work
    cp -r /app/content /app/content-work

    # Apply direct template substitution to working content files
    find /app/content-work -name "*.md" -type f | while read -r file; do
        # Skip if file doesn't exist or is not readable
        [ -r "$file" ] || continue

        # Create temporary file
        temp_file=$(mktemp)

        # Apply substitutions using | delimiter to avoid issues with special characters
        PDF_FILENAME="$(echo "$PERSON_NAME" | tr ' ' '-')-Emergency-Plan.pdf"
        sed -e "s|{{ person.name }}|$PERSON_NAME|g" \
            -e "s|{{ person.pronouns }}|$PERSON_PRONOUNS|g" \
            -e "s|{{ person.relationship }}|$PERSON_RELATIONSHIP|g" \
            -e "s|{{ plan.title }}|$PLAN_TITLE|g" \
            -e "s|{{ plan.subtitle }}|$PLAN_SUBTITLE|g" \
            -e "s|{{ plan.description }}|What to do if something happens to $PERSON_NAME|g" \
            -e "s|{{ branding.site_name }}|$PLAN_TITLE|g" \
            -e "s|{{ branding.pdf_filename }}|$PDF_FILENAME|g" \
            -e "s|{{ branding.author }}|$PERSON_NAME|g" \
            -e "s|Hit-By-A-Bus-Plan.pdf|$PDF_FILENAME|g" \
            "$file" > "$temp_file"

        # Replace working file
        mv "$temp_file" "$file"
    done

    # Create a personalized mkdocs.yml pointing to working content
    if [ -f "/app/site-template/mkdocs.yml" ]; then
        # Only update if we haven't already personalized (check for content-work reference)
        if ! grep -q "content-work" "/app/site/mkdocs.yml" 2>/dev/null; then
            echo "🔧 Personalizing mkdocs.yml..."
            temp_file=$(mktemp)
            sed -e "s|docs_dir: ../content|docs_dir: ../content-work|g" \
                -e "s|Hit By A Bus Plan|$PLAN_TITLE|g" \
                -e "s|Emergency plan and important information guide|What to do if something happens to $PERSON_NAME|g" \
                -e "s|Your Name Here|$PERSON_NAME|g" \
                "/app/site-template/mkdocs.yml" > "$temp_file"
            mv "$temp_file" "/app/site/mkdocs.yml"
        else
            echo "✅ mkdocs.yml already personalized"
        fi
    fi

    echo "✅ Personalisation applied to working copy"
fi

# Check personalisation requirement
if [ "$REQUIRE_PERSONALISATION" = "true" ]; then
    if [ -z "$PERSON_NAME" ] || [ "$PERSON_NAME" = "Your Name Here" ] || [ "$PERSON_NAME" = "Your Name" ] || [ "$PERSON_NAME" = "John Smith" ]; then
        echo "❌ PERSONALISATION REQUIRED"
        echo "=============================="
        echo "This emergency plan must be personalised before use."
        echo ""
        echo "Quick setup:"
        echo "  1. cp .env.example .env"
        echo "  2. Edit PERSON_NAME='Your Name' in .env"
        echo "  3. docker-compose up"
        echo ""
        echo "Or set directly:"
        echo "  PERSON_NAME='Your Name' docker-compose up"
        echo ""
        echo "Or to skip this check:"
        echo "  REQUIRE_PERSONALISATION=false docker-compose up"
        echo ""
        exit 1
    fi
    echo "✅ Personalised for: $PERSON_NAME"
fi

# Check Pandoc for PDF generation
if command -v pandoc >/dev/null 2>&1; then
    echo "✅ Pandoc found for PDF generation"
else
    echo "⚠️  Warning: Pandoc not found - PDF generation may fail"
fi

# Function to cleanup background processes
cleanup() {
    echo "🛑 Shutting down services..."
    jobs -p | xargs -r kill 2>/dev/null || true
    wait
    echo "✅ Cleanup complete"
}

# Setup signal handlers
trap cleanup EXIT INT TERM

# Ensure output directory exists
mkdir -p /app/output

# Run security scan
echo "🔍 Running comprehensive security scan..."
scan_failed=false

# 1. detect-secrets scan
if command -v detect-secrets >/dev/null 2>&1; then
    cd /app && detect-secrets scan --all-files >/dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "⚠️  detect-secrets found issues"
        scan_failed=true
    fi
else
    echo "⚠️  detect-secrets not available"
fi

# 2. Generic secrets scan (credit cards, IBANs, etc)
if [ -f "/app/scripts/scan_generic_secrets.py" ]; then
    python3 /app/scripts/scan_generic_secrets.py /app/content --exit-code --quiet >/dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "⚠️  Generic secrets scan found financial data:"
        python3 /app/scripts/scan_generic_secrets.py /app/content --json 2>/dev/null | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    for item in data[:3]:  # Show first 3 findings
        print(f\"  {item['type']} in {item['file']}:{item['line']} - {item['value_masked']}\")
    if len(data) > 3:
        print(f\"  ... and {len(data)-3} more findings\")
except:
    pass
"
        scan_failed=true
    fi
fi

if [ "$scan_failed" = "true" ]; then
    echo "⚠️  Security scans found issues - please review content"
else
    echo "✅ Security scans passed"
fi

# Generate PDF if possible
echo "📄 Generating PDF..."
if command -v python3 >/dev/null 2>&1 && [ -f "/app/scripts/pandoc_pdf.py" ]; then
    cd /app && python3 scripts/pandoc_pdf.py || echo "⚠️  PDF generation failed"
else
    echo "⚠️  PDF generation skipped - pandoc_pdf.py not found"
fi

# Start MkDocs server
echo "🌐 Starting MkDocs server on ${MKDOCS_HOST}:${MKDOCS_PORT}..."
cd /app/site
mkdocs serve -a "${MKDOCS_HOST}:${MKDOCS_PORT}" &
MKDOCS_PID=$!

# Wait for MkDocs to start
sleep 5

# Start Editor server if enabled
if [ "$ENABLE_EDITOR" = "true" ]; then
    echo "✏️  Starting Editor server on ${EDITOR_HOST}:${EDITOR_PORT}..."
    cd /app/editor
    python app.py &
    EDITOR_PID=$!

    # Wait for Editor to start
    sleep 3

    echo ""
    echo "🎉 Started with live editing enabled!"
    echo "====================================="
    echo "📖 MkDocs Site:    http://localhost:${MKDOCS_PORT}"
    echo "✏️  Editor:         http://localhost:${EDITOR_PORT}"
    echo "📄 PDF Download:    http://localhost:${MKDOCS_PORT}/Hit-By-A-Bus-Plan.pdf"
    echo ""
    echo "💡 Access the editor to make live changes to your emergency plan"
else
    echo ""
    echo "📖 Site started (editor disabled)"
    echo "================================="
    echo "📖 MkDocs Site:    http://localhost:${MKDOCS_PORT}"
    echo "📄 PDF Download:    http://localhost:${MKDOCS_PORT}/Hit-By-A-Bus-Plan.pdf"
    echo ""
    echo "💡 To enable editing, set ENABLE_EDITOR=true"
fi

echo ""

# Wait for processes
wait
