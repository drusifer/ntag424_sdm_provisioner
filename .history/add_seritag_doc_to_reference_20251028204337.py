#!/usr/bin/env python3
"""
Add the Seritag authentication document to our focused investigation reference.
"""

import fitz
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

def add_seritag_document():
    """Add all pages of the Seritag authentication document to investigation reference."""
    
    pdf_path = "nfc_tag_auth_explained_seritag.pdf"
    output_dir = Path("investigation_ref")
    
    if not Path(pdf_path).exists():
        log.error(f"Seritag PDF not found: {pdf_path}")
        return
    
    log.info("Adding Seritag authentication document to investigation reference...")
    
    # Extract all pages from the Seritag document
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    
    seritag_pages = []
    
    for page_num in range(1, total_pages + 1):
        try:
            page = doc[page_num - 1]  # 0-indexed
            
            # Export as SVG
            svg_content = page.get_svg_image(matrix=fitz.Identity)
            
            # Save SVG
            filename = f"seritag_auth_page_{page_num:02d}.svg"
            filepath = output_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(svg_content)
            
            seritag_pages.append((page_num, f"Seritag Authentication - Page {page_num}", filepath))
            log.info(f"  Added Seritag page {page_num}/{total_pages}")
            
        except Exception as e:
            log.error(f"Failed to extract Seritag page {page_num}: {e}")
    
    doc.close()
    
    # Update the investigation reference markdown
    update_reference_markdown(seritag_pages)
    
    log.info(f"✅ Added {len(seritag_pages)} Seritag pages to investigation reference")

def update_reference_markdown(seritag_pages):
    """Update the investigation reference to include Seritag document."""
    
    ref_file = Path("investigation_ref/seritag_investigation_reference.md")
    
    if not ref_file.exists():
        log.error("Investigation reference file not found!")
        return
    
    # Read current content
    with open(ref_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find where to insert Seritag section (after the quick reference, before NXP spec)
    insert_marker = "## 📖 NXP NTAG424 DNA Specification"
    
    if insert_marker not in content:
        log.error("Could not find insertion point in reference file!")
        return
    
    # Create Seritag section
    seritag_section = [
        "## 🎯 Seritag Authentication Document",
        "",
        "**CRITICAL: This document explains Seritag's authentication implementation**",
        "",
    ]
    
    for page_num, description, filepath in seritag_pages:
        rel_path = filepath.name
        seritag_section.extend([
            f"### {description}",
            "",
            f"![Seritag Page {page_num}]({rel_path})",
            "",
            "---",
            "",
        ])
    
    # Insert Seritag section before NXP spec
    seritag_content = "\n".join(seritag_section)
    updated_content = content.replace(insert_marker, seritag_content + insert_marker)
    
    # Create backup
    backup_file = ref_file.with_suffix('.md.backup-before-seritag')
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # Write updated content
    with open(ref_file, 'w', encoding='utf-8') as f:
        f.write(updated_content)
    
    log.info("✅ Updated investigation reference with Seritag document")

def main():
    """Main function."""
    add_seritag_document()
    
    log.info("🎯 Seritag document added to investigation reference!")
    log.info("   - This should explain their authentication modifications")
    log.info("   - Critical for understanding Phase 2 protocol differences")
    log.info("   - May reveal the purpose of command 0x51")

if __name__ == "__main__":
    main()
