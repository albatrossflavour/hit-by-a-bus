<div align="center">
  <img src="assets/images/logo.png" alt="Hit By A Bus Plan Logo" width="200">

  # Hit By A Bus Plan

  *A self-hostable, open source emergency information plan using MkDocs Material.*

  This project provides a structured way to document and organize critical information that loved ones would need access to in an emergency.
</div>

## Features

- 📚 **Static Site**: Built with MkDocs Material for clean, searchable documentation
- 📄 **PDF Export**: Generate professional PDFs using Pandoc + LaTeX
- 🐳 **Self-Hostable**: Docker and docker-compose ready for easy deployment
- ✏️ **Live Editing**: Web-based editor for non-technical users
- 👤 **Personalisable**: Easily customisable for different people
- 🔍 **Search Enabled**: Full-text search across all content
- 📱 **Responsive**: Works on desktop, tablet, and mobile
- 🖨️ **Print Optimised**: CSS optimised for clean printing
- 🔒 **Security First**: No secrets stored in repo - only references to where they're located

## Quick Start

### Docker Setup (Recommended)

```bash
# 1. Personalise your plan
cp .env.example .env
edit .env  # Set PERSON_NAME to your name

# 2. Choose your mode:
PERSON_NAME="Your Name" make docker-run    # Basic mode (site only)
PERSON_NAME="Your Name" make docker-edit   # With live web editor

# Visit:
# http://localhost:8000 - Your emergency plan site
# http://localhost:8001 - Web editor (if enabled)
```

### Local Development

```bash
# 1. Install dependencies
make setup

# 2. Personalise for yourself
cp .env.example .env && edit .env

# 3. Start development server
make serve

# 4. Generate PDF
make pdf
```

## Configuration & Personalisation

### Example .env Configuration

```env
# Required: Personalisation
PERSON_NAME=Your Name Here
PERSON_PRONOUNS=they/them
PERSON_RELATIONSHIP=me

# Plan details
PLAN_TITLE=Hit By A Bus Plan
PLAN_SUBTITLE=Emergency Information Guide

# Feature toggles
ENABLE_EDITOR=false
REQUIRE_PERSONALISATION=true

# Network settings (optional)
MKDOCS_HOST=0.0.0.0
MKDOCS_PORT=8000
EDITOR_HOST=0.0.0.0
EDITOR_PORT=8001
```

## Content Architecture & Design

### Why This Content Structure Works

This project uses a **hybrid metadata + markdown approach** rather than pure data files. Here's why:

**✅ Current Approach:**
```yaml
---
title: "Household and Finances"
updated: "2025-08-13"
summary: "Banking, bills, household expenses, and financial obligations"
critical: true
---
# Household and Finances

## Summary
Complete financial picture including bank accounts, recurring bills...

## What to do
- Secure access to primary bank accounts
- Review and maintain recurring payments
```

**❌ Pure Metadata Would Be:**
```yaml
banking:
  accounts:
    - type: checking
      bank: "[Bank name]"
      account_ending: "XXXX"
      online_access: "[Website/app]"
      branch_location: "[Address]"
      statements_location: "[Paper/digital location]"
    # This gets unwieldy fast for complex information
```

**Why the hybrid approach works better:**

1. **Complex Information** - Emergency plans contain varied, complex data that doesn't fit neatly into structured formats
2. **Human Readability** - Markdown allows for explanations, instructions, and formatting that makes information accessible during stressful times
3. **Cross-References** - Easy to link between sections and provide context
4. **Flexibility** - Each section can have different information structures while maintaining consistency

**Design Principle**: Use metadata for what the system needs (titles, flags, dates), use markdown for what humans need (instructions, context, formatted information).

## Content Organization

Each section follows a three-part structure:

- **Summary**: What this section covers
- **What to do**: Specific actions to take
- **Where it is**: Locations of documents, accounts, contacts

### Adding New Content Sections

When creating new sections:

1. **Start with metadata**: Include title, summary, updated date, and critical flag if needed
2. **Follow the three-part format**: Summary → What to do → Where it is
3. **Use references, not secrets**: Store locations of information, never actual passwords or sensitive data
4. **Add to navigation**: Update `site/mkdocs.yml` with your new section
5. **Consider priority**: Where does this fit in the emergency response timeline?

### Sections (Priority Order)

1. **🚨 Critical** (first 24-48 hours):
   - Overview & Start Here
   - Personal Information
   - Emergency Contacts
   - Digital Access

2. **📋 Important** (first week):
   - Household & Finances
   - Legal & Medical

3. **📝 Standard** (ongoing):
   - Jobs & Work
   - Infrastructure & Systems
   - Ongoing Commitments
   - Personal Wishes
   - Physical Documents

## Development Commands

```bash
# Setup
make setup-env        # Create .env from template
make setup            # Install dependencies

# Development
make serve            # Local development server
make build            # Build static site
make pdf              # Generate PDF with Pandoc
make clean            # Remove build artifacts

# Docker
make docker-run       # Basic mode
make docker-edit      # With editor enabled
make docker-stop      # Stop container

# Security
make security-scan     # Scan for accidentally committed secrets
make security-audit    # Run comprehensive security checks
```

## Live Web Editor

The built-in web editor provides:

✅ **Form-based editing** - No markdown knowledge required
✅ **Auto-save drafts** - Saves progress locally
✅ **Live preview** - See changes immediately
✅ **Auto-rebuild** - Site updates when you save
✅ **Security guidance** - Reminds what not to store
✅ **Automatic security scanning** - Scans for accidentally committed secrets on every save

Access at `http://localhost:8001` when running with `ENABLE_EDITOR=true`.

## PDF Generation

```bash
make pdf
```

Uses Pandoc + LaTeX for professional typography:

- **High-quality output** with proper page breaks and margins
- **Professional formatting** with table of contents
- **Reliable generation** without browser dependencies
- Requires: `pandoc` and `texlive` (included in Docker)

## Deployment Options

### Static Hosting

Deploy `output/site/` to:

- Netlify, Vercel, GitHub Pages
- Your own web server
- Cloud storage with web hosting

### Self-Hosting with Docker

The Docker deployment mounts your local content directory for security:

```bash
# Set your name and run
PERSON_NAME="Your Name" make docker-run    # Basic mode (secure)
PERSON_NAME="Your Name" make docker-edit   # With live web editor

# Or use environment file
cp .env.example .env  # Edit PERSON_NAME
docker-compose up
```

**Key Security Benefits:**

- ✅ **No personal data in images**: Your emergency plan content is never embedded in Docker images
- ✅ **Portable**: The same image works for everyone - content is external
- ✅ **Updatable**: Update content by editing local files
- ✅ **Shareable**: The Docker image can be shared safely without exposing personal info

### Security Considerations

Since this contains emergency information routing:

- **VPN access**: Host behind VPN for family access
- **Basic Auth**: Simple username/password protection
- **OAuth**: Google/GitHub authentication
- **Cloudflare Access**: Zero-trust access control

## Project Structure

```text
hit-by-a-bus/
├── .env.example               # Environment configuration template
├── content/                   # Markdown content files (templates)
│   ├── index.md              # Homepage template
│   ├── 01-overview.md        # Start here template
│   ├── 02-personal-info.md   # Identity info template
│   └── ...                   # Other section templates
├── site/
│   ├── mkdocs.yml            # MkDocs configuration
│   └── overrides/            # Theme customizations
├── editor/                   # Live web editor
│   ├── app.py               # FastAPI application
│   └── templates/           # Editor HTML templates
├── scripts/
│   ├── docker-entrypoint.sh   # Docker container startup
│   ├── init-user-content.sh   # Docker initialization
│   ├── pandoc_pdf.py          # PDF generation
│   └── scan_generic_secrets.py # Security scanning
├── docker-compose.yml       # Container orchestration with volumes
├── Dockerfile               # Application-only container (no personal data)
└── Makefile                 # Build automation
```

**🔒 Security Architecture:**

- **Templates**: Source code contains only templates and examples
- **User content**: Stored in Docker volumes or local directories (not in images)
- **Configuration**: Personalization through external config files
- **Separation**: Clear boundary between application code and personal data

## Security Best Practices

### What to Store

✅ **References** to where information is located
✅ **Instructions** on how to access accounts
✅ **Contact information** for people and institutions
✅ **Locations** of important documents

### What NOT to Store

❌ **Actual passwords** or sensitive data
❌ **Account numbers** or secrets
❌ **Social Security Numbers** or IDs
❌ **Credit card numbers** or PINs

### Automated Security Scanning

This project includes comprehensive security scanning to catch accidentally committed sensitive data:

```bash
# Install security scanner (optional - included in Docker)
pip install detect-secrets

# Run comprehensive security scan
make security-scan

# Full security audit
make security-audit
```

**Enhanced Scanner Detects:**

- **Passwords and API keys** (detect-secrets)
- **Credit card numbers** (Luhn validation + brand detection)
- **IBANs** (with checksum validation)
- **US routing numbers** (ABA validation)
- **UK sort codes and account numbers**
- **Australian BSB codes**
- **Canadian transit/institution codes**
- **Indian IFSC codes**
- **Private keys and certificates**
- **Database connection strings**
- **Other financial and sensitive patterns**

### Integrated Security Workflow

Comprehensive security scanning runs automatically at multiple points:

1. **Container startup**: Full scan runs when Docker container starts
2. **Build process**: `make build` runs comprehensive scan before building the site
3. **Live editor**: Security scan runs automatically when content is saved through the web editor
4. **Manual scanning**: Run `make security-scan` for on-demand comprehensive scanning
5. **Docker deployment**: Both scanners are included in the container image

**Real-time Protection**: Every edit is automatically scanned for sensitive data before saving.

### Content Examples

**✅ Good:**

```markdown
- Bank: First National Bank
- Account: Checking ending in 1234
- Online access: firstnational.com
- Password: Stored in 1Password vault "Banking"
- Branch: 123 Main St, (555) 123-4567
```

**❌ Bad:**

```markdown
- Username: john.smith@email.com
- Password: mySecretPassword123
- Account: 1234567890123456
```

## Contributing

This project is designed to be forked and customized for individual/family use. For the base template:

1. Keep security best practices
2. Maintain the three-section content format
3. Ensure mobile-friendly design
4. Test PDF generation
5. Verify Docker deployment

## License

This project template is provided as-is for personal use. The content you create is your own. Be mindful of security and privacy when sharing or hosting your version.

---

**Remember**: This is your emergency plan. Keep it updated, secure, and accessible to those who need it. The goal is to make a difficult time easier for your loved ones.
