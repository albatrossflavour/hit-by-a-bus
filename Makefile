# Hit By A Bus Plan - Makefile
# Static site generator and PDF export automation

.PHONY: help setup setup-env build serve pdf clean security-scan security-audit docker-build docker-run docker-edit docker-stop

# Default target
help:
	@echo "Hit By A Bus Plan - Available targets:"
	@echo ""
	@echo "Quick Start:"
	@echo "  setup-env       Create .env file from template"
	@echo "  docker-run      Run basic mode"
	@echo "  docker-edit     Run with editor enabled"
	@echo ""
	@echo "Security:"
	@echo "  security-scan   Scan for accidentally committed secrets"
	@echo "  security-audit  Run comprehensive security checks"
	@echo ""
	@echo "Development:"
	@echo "  setup           Install MkDocs and required plugins"
	@echo "  build           Build the static site"
	@echo "  serve           Serve the site locally for development"
	@echo "  pdf             Generate PDF using Pandoc"
	@echo "  clean           Remove output directory"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build    Build Docker image"
	@echo "  docker-run      Run with editor disabled"
	@echo "  docker-edit     Run with editor enabled"
	@echo "  docker-stop     Stop container"
	@echo ""

# Install dependencies
setup:
	@echo "Installing MkDocs Material..."
	pip install mkdocs-material
	@echo ""
	@echo "For PDF generation, install Pandoc:"
	@echo "  macOS: brew install pandoc basictex"
	@echo "  Ubuntu: apt install pandoc texlive-latex-base texlive-fonts-recommended"
	@echo ""
	@echo "Setup complete! Copy .env.example to .env and edit, then 'make serve' to start."
	@echo ""
	@echo "Optional security scanning:"
	@echo "  pip install detect-secrets"
	@echo "  make security-scan"

# Configuration commands
setup-env:
	@echo "Creating .env file from template..."
	@if [ ! -f ".env" ]; then \
		cp .env.example .env; \
		echo "✅ Created .env file. Edit it with your details:"; \
		echo "   PERSON_NAME='Your Name'"; \
	else \
		echo "⚠️  .env file already exists"; \
	fi

# Build the static site
build:
	@echo "Building static site..."
	@echo "🔍 Running security scan..."
	@make security-scan
	cd site && mkdocs build -d ../output/site
	@echo "Site built in output/site/"

# Serve locally for development
serve:
	@echo "Starting development server at http://localhost:8000"
	@echo "Press Ctrl+C to stop"
	cd site && mkdocs serve -a 0.0.0.0:8000

# Generate PDF using Pandoc
pdf:
	@echo "Generating PDF with Pandoc..."
	@echo "Note: Requires pandoc and texlive. Install with: brew install pandoc basictex"
	python scripts/pandoc_pdf.py
	@if [ -f "output/Hit-By-A-Bus-Plan.pdf" ]; then \
		echo "✅ PDF generated: output/Hit-By-A-Bus-Plan.pdf"; \
	else \
		echo "❌ PDF generation failed"; \
	fi

# Clean output directory
clean:
	@echo "Cleaning output directory..."
	rm -rf output/
	@echo "Output directory removed."


# Security scanning
security-scan:
	@echo "🔍 Running comprehensive security scan..."
	@scan_failed=false; \
	\
	if command -v detect-secrets >/dev/null 2>&1; then \
		SCAN_RESULT=$$(detect-secrets scan --all-files 2>/dev/null); \
		if echo "$$SCAN_RESULT" | grep -q '"results": {}'; then \
			echo "✅ detect-secrets: no secrets detected"; \
		else \
			echo "🚨 detect-secrets found issues:"; \
			if command -v jq >/dev/null 2>&1; then \
				echo "$$SCAN_RESULT" | jq -r '.results | to_entries[] | "  " + .key + ":" + (.value[] | " line " + (.line_number | tostring) + " (" + .type + ")")'; \
			else \
				echo "$$SCAN_RESULT"; \
			fi; \
			scan_failed=true; \
		fi; \
	else \
		echo "⚠️  detect-secrets not installed. Run: pip install detect-secrets"; \
	fi; \
	\
	if [ -f "scripts/scan_generic_secrets.py" ]; then \
		if python3 scripts/scan_generic_secrets.py content --exit-code --quiet >/dev/null 2>&1; then \
			echo "✅ Generic scan: no financial data detected"; \
		else \
			echo "🚨 Financial data detected:"; \
			python3 scripts/scan_generic_secrets.py content --json 2>/dev/null | python3 -c "import json, sys; data = json.load(sys.stdin); [print(f'  {item[\"file\"]}:{item[\"line\"]} {item[\"type\"]} - {item[\"value_masked\"]}') for item in data[:5]] if data else None"; \
			scan_failed=true; \
		fi; \
	else \
		echo "⚠️  Generic secrets scanner not found"; \
	fi; \
	\
	if [ "$$scan_failed" = "true" ]; then \
		echo ""; \
		echo "❌ Security issues found - please review and remove sensitive data"; \
		echo "💡 Store only references like 'Account details in 1Password vault'"; \
		exit 1; \
	else \
		echo "✅ Comprehensive security scan complete - no issues detected"; \
	fi

security-audit:
	@echo "🛡️  Running comprehensive security audit..."
	@echo ""
	@echo "1. Scanning for secrets..."
	@make security-scan
	@echo ""
	@echo "2. Checking for common security issues..."
	@echo "✅ No actual passwords should be stored in content files"
	@echo "✅ Use references like 'Stored in 1Password' instead of actual secrets"
	@echo "✅ Check that placeholder values like '[Your bank name]' are replaced"
	@echo ""
	@echo "3. Validating content structure..."
	@make validate
	@echo ""
	@echo "🎯 Security audit complete!"

# Build Docker image
docker-build:
	@echo "Building Docker image..."
	docker build -t hit-by-a-bus-plan .
	@echo "Docker image built: hit-by-a-bus-plan"

# Run with editor disabled
docker-run:
	@echo "Starting Hit By A Bus Plan (editor disabled)..."
	@echo "Site will be available at http://localhost:8000"
	@echo ""
	@echo "💡 Setup .env file first:"
	@echo "   cp .env.example .env && edit .env"
	@echo "   (or set PERSON_NAME='Your Name' before running)"
	docker-compose up

# Run with editor enabled
docker-edit:
	@echo "Starting Hit By A Bus Plan with editor..."
	@echo "Site: http://localhost:8000"
	@echo "Editor: http://localhost:8001"
	@echo ""
	@echo "💡 Setup .env file first:"
	@echo "   cp .env.example .env && edit .env"
	@echo "   (or set PERSON_NAME='Your Name' ENABLE_EDITOR=true before running)"
	ENABLE_EDITOR=true docker-compose up

# Stop container
docker-stop:
	@echo "Stopping container..."
	docker-compose down

# Quick setup helper (deprecated - use setup-env instead)
# production-setup: setup-env


# Development workflow
dev-setup: setup
	@echo "Development setup complete!"
	@echo "To get started:"
	@echo "  1. Edit content files in content/"
	@echo "  2. Run 'make serve' to preview changes"
	@echo "  3. Run 'make pdf' to generate PDF"

# Production build
prod-build: clean build pdf
	@echo "Production build complete!"
	@echo "Files ready for deployment:"
	@echo "  - Static site: output/site/"
	@echo "  - PDF: output/Hit-By-A-Bus-Plan.pdf"

# Quick content update workflow
update: build pdf
	@echo "Content updated and PDF regenerated!"

# Check if required tools are installed
check:
	@echo "Checking for required tools..."
	@which python3 > /dev/null || (echo "❌ Python3 not found" && exit 1)
	@which pip > /dev/null || (echo "❌ pip not found" && exit 1)
	@python3 -c "import mkdocs" 2>/dev/null || echo "⚠️  MkDocs not installed (run 'make setup')"
	@python3 -c "import material" 2>/dev/null || echo "⚠️  MkDocs Material not installed (run 'make setup')"
	@which docker > /dev/null || echo "⚠️  Docker not found (needed for containerization)"
	@echo "✅ Tool check complete"

# Validate content files
validate:
	@echo "Validating content files..."
	@for file in content/*.md; do \
		echo "Checking $$file..."; \
		head -n 10 "$$file" | grep -q "^---$$" || (echo "❌ Missing YAML front matter in $$file" && exit 1); \
	done
	@echo "✅ All content files have proper YAML front matter"

# Show file sizes and summary
info:
	@echo "Hit By A Bus Plan - Project Info"
	@echo "================================="
	@echo "Content files:"
	@ls -la content/ | grep -E "\.md$$" | wc -l | xargs echo "  Total markdown files:"
	@du -sh content/ | cut -f1 | xargs echo "  Content directory size:"
	@echo ""
	@if [ -d "output/" ]; then \
		echo "Output files:"; \
		du -sh output/ | cut -f1 | xargs echo "  Output directory size:"; \
		if [ -f "output/Hit-By-A-Bus-Plan.pdf" ]; then \
			ls -lh output/Hit-By-A-Bus-Plan.pdf | awk '{print "  PDF size: " $$5}'; \
		fi; \
	else \
		echo "No output files (run 'make build' or 'make pdf')"; \
	fi
