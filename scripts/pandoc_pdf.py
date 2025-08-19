#!/usr/bin/env python3
"""
Hit By A Bus Plan - Pandoc PDF Generator
Simple, reliable PDF generation using Pandoc + LaTeX
"""

import subprocess
import sys
import re
from pathlib import Path
import yaml
from datetime import date

def clean_unicode_for_latex(text: str) -> str:
    """Remove Unicode characters that cause LaTeX issues"""
    # Remove emojis, variation selectors, and other problematic Unicode
    text = re.sub(r'[\U0001F600-\U0001F64F]', '', text)  # Emoticons
    text = re.sub(r'[\U0001F300-\U0001F5FF]', '', text)  # Misc symbols
    text = re.sub(r'[\U0001F680-\U0001F6FF]', '', text)  # Transport
    text = re.sub(r'[\U0001F1E0-\U0001F1FF]', '', text)  # Flags
    text = re.sub(r'[\U00002600-\U000027BF]', '', text)  # Misc symbols
    text = re.sub(r'[\U0000FE00-\U0000FE0F]', '', text)  # Variation selectors
    text = re.sub(r'[\U0000200D]', '', text)             # Zero width joiner
    text = re.sub(r'[\U0000202A-\U0000202E]', '', text)  # Text direction
    return text.strip()

def generate_pdf():
    """Generate PDF using Pandoc from markdown files"""

    content_dir = Path("/app/content-work") if Path("/app/content-work").exists() else Path("/app/content")
    output_dir = Path("/app/output")
    site_output = Path("/app/output/site")

    # Ensure directories exist
    output_dir.mkdir(exist_ok=True)
    site_output.mkdir(exist_ok=True)

    print("📄 Generating PDF using Pandoc...")

    # Get all content files in order
    content_files = sorted([
        f for f in content_dir.glob("*.md")
        if not f.name.startswith('.') and not f.name.endswith('.pdf')
    ])

    if not content_files:
        print("❌ No content files found")
        return False

    # Create combined markdown
    combined_md = create_combined_markdown(content_files)
    temp_md = output_dir / "combined.md"

    with open(temp_md, 'w', encoding='utf-8') as f:
        f.write(combined_md)

    # Get personalized filename from environment or use default
    person_name = os.getenv('PERSON_NAME', 'Hit-By-A-Bus')
    pdf_filename = f"{person_name.replace(' ', '-')}-Emergency-Plan.pdf" if person_name != 'Hit-By-A-Bus' else "Hit-By-A-Bus-Plan.pdf"

    # PDF output paths - use personalized name
    pdf_path = output_dir / pdf_filename
    site_pdf = site_output / pdf_filename

    # Pandoc command
    pandoc_cmd = [
        "pandoc",
        str(temp_md),
        "-o", str(pdf_path),
        "--pdf-engine=pdflatex",
        "--variable", "geometry:margin=1in",
        "--variable", "fontsize=11pt",
        "--variable", "documentclass=article",
        "--variable", "pagestyle=headings",
        "--table-of-contents",
        "--toc-depth=2",
        "--highlight-style=tango",
        "--metadata", "title=Hit By A Bus Plan",
        "--metadata", "author=Emergency Information Guide",
        "--metadata", f"date={date.today().strftime('%B %d, %Y')}",
    ]

    try:
        # Run Pandoc
        result = subprocess.run(
            pandoc_cmd,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            print(f"✅ PDF generated successfully: {pdf_path}")

            # Copy to site directory for web access
            import shutil
            shutil.copy2(pdf_path, site_pdf)
            print(f"✅ PDF copied to site: {site_pdf}")

            # Also copy to content directory so MkDocs can serve it
            content_pdf = content_dir / pdf_filename
            shutil.copy2(pdf_path, content_pdf)
            print(f"✅ PDF copied for web access: {content_pdf}")

            # Cleanup
            temp_md.unlink()

            return True
        else:
            print(f"❌ Pandoc failed: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print("❌ Pandoc timed out")
        return False
    except Exception as e:
        print(f"❌ PDF generation failed: {e}")
        return False

def create_combined_markdown(content_files):
    """Combine all markdown files into one document"""

    combined = f"""---
title: "Hit By A Bus Plan"
subtitle: "Emergency Information Guide"
author: "Personal Emergency Plan"
date: "{date.today().strftime('%B %d, %Y')}"
geometry: margin=1in
fontsize: 11pt
documentclass: article
pagestyle: headings
toc: true
toc-depth: 2
---

\\newpage

"""

    for file_path in content_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse front matter
            if content.startswith('---\n'):
                parts = content.split('---\n', 2)
                if len(parts) >= 3:
                    front_matter = yaml.safe_load(parts[1]) or {}
                    body = parts[2].strip()
                else:
                    front_matter = {}
                    body = content
            else:
                front_matter = {}
                body = content

            # Add section header
            title = front_matter.get('title', 'Section')
            critical = front_matter.get('critical', False)
            updated = front_matter.get('updated', '')

            # Remove emojis and problematic Unicode for PDF
            title_clean = clean_unicode_for_latex(title)

            combined += f"\n\\newpage\n\n"

            if critical:
                combined += f"# {title_clean} (CRITICAL)\n\n"
                combined += "> **Critical Section**: This information requires immediate attention in an emergency.\n\n"
            else:
                combined += f"# {title_clean}\n\n"

            if updated:
                combined += f"*Last updated: {updated}*\n\n"

            # Remove emojis and problematic Unicode from body content for PDF
            body_clean = clean_unicode_for_latex(body)

            # Add body content
            combined += body_clean + "\n\n"

        except Exception as e:
            print(f"Warning: Could not process {file_path}: {e}")
            continue

    return combined

if __name__ == "__main__":
    success = generate_pdf()
    sys.exit(0 if success else 1)
