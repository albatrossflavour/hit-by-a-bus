# Hit By A Bus Plan - Claude Code Context

## Project Overview

This is a **hit-by-a-bus emergency information plan** system - a self-hostable documentation platform for organizing critical information that loved ones would need in an emergency. Built with MkDocs Material, Docker, and includes a live web editor.

**Purpose**: Help people document emergency information safely and securely, with automated scanning to prevent accidentally storing sensitive data.

## Architecture

- **Static Site**: MkDocs Material-based documentation site
- **PDF Export**: Pandoc + LaTeX for professional PDF generation
- **Live Editor**: FastAPI-based web editor for non-technical users
- **Docker**: Containerized deployment with security-first design
- **Content Security**: Automated scanning prevents accidental storage of sensitive data

## Key Directories

```
hit-by-a-bus/
├── content/              # Markdown content templates (user edits these)
├── site/                 # MkDocs configuration and theme
├── editor/               # FastAPI web editor application
├── scripts/              # Build and security scanning scripts
├── output/               # Generated site and PDF files
└── docker-compose.yml    # Container orchestration
```

## Development Commands

**Local Development:**
- `make setup` - Install MkDocs Material dependencies
- `make serve` - Start development server (localhost:8000)
- `make build` - Build static site (includes security scan)
- `make pdf` - Generate PDF with Pandoc
- `make security-scan` - Comprehensive security scanning

**Docker:**
- `make docker-run` - Basic mode (site only)
- `make docker-edit` - With live web editor enabled
- `PERSON_NAME="Name" make docker-run` - Personalized deployment

## Key Files

- **Makefile** - Build automation with security scanning
- **site/mkdocs.yml** - MkDocs configuration (uses content-work/ as source)
- **editor/app.py** - FastAPI web editor
- **scripts/scan_generic_secrets.py** - Financial/sensitive data scanner
- **content/*.md** - Content templates (user personalizes these)

## Technology Stack

**Frontend:**
- MkDocs Material (static site generator)
- Material Design theme with print optimization
- Full-text search enabled

**Backend (Editor):**
- FastAPI (Python web framework)
- Jinja2 templates
- File watching with automatic rebuild

**Dependencies:**
- Python 3 + MkDocs Material
- Pandoc + LaTeX (for PDF)
- Docker + docker-compose
- Optional: detect-secrets for enhanced security scanning

## Security Model

**Critical Security Features:**
1. **No sensitive data storage** - Only references to where information is located
2. **Automated scanning** - Prevents accidental commit of passwords, account numbers, etc.
3. **Docker security** - Personal data never embedded in images
4. **Template-based** - Source code contains only templates and examples

**Security Scanning:**
- Built-in financial data detection (credit cards, IBANs, routing numbers, etc.)
- Integration with detect-secrets for password/API key detection
- Automatic scanning on build, save, and container startup

## Content Structure

Each section follows a three-part format:
1. **Summary** - What this section covers
2. **What to do** - Specific actions to take
3. **Where it is** - Locations of documents, accounts, contacts

**Priority Levels:**
- **🚨 Critical** (first 24-48 hours): Overview, Personal Info, Emergency Contacts, Digital Access
- **📋 Important** (first week): Household & Finances, Legal & Medical
- **📝 Standard** (ongoing): Jobs, Infrastructure, Commitments, Personal Wishes, Physical Documents

## Personalization

The system uses template variables and environment files:
- `.env` file for personalization (PERSON_NAME, etc.)
- Template content with `{{ person.name }}` placeholders
- Docker volume mounting keeps personal data separate from images

## Build Process

1. Security scan runs automatically before build
2. Content templates are personalized with user data
3. MkDocs generates static site
4. Optional PDF generation with Pandoc
5. Output goes to `output/site/` and `output/Hit-By-A-Bus-Plan.pdf`

## Common Tasks

**Setting up for a new person:**
1. Copy `.env.example` to `.env`
2. Edit `.env` with person's details
3. Run `make docker-run` or `make serve`

**Adding new content sections:**
1. Create new `.md` file in `content/`
2. Add to navigation in `site/mkdocs.yml`
3. Follow existing three-part format

**Security maintenance:**
- Run `make security-scan` regularly
- Never store actual passwords or account numbers
- Use references like "Stored in 1Password vault 'Banking'"
