#!/usr/bin/env python3
"""
Convert entire PDF to page-by-page SVGs and create markdown with embedded SVGs.

This approach preserves all content (text + graphics) as scalable vectors.
"""

import fitz  # PyMuPDF
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

class PDFToSVGConverter:
    """Convert PDF pages to SVG and create markdown."""
    
    def __init__(self, pdf_path: str, output_name: str = "nxp-ntag424-complete"):
        self.pdf_path = Path(pdf_path)
        self.output_name = output_name
        self.pages_dir = Path(f"pages/{output_name}")
        self.md_path = Path(f"{output_name}.md")
        
    def convert_pdf_to_pages(self):
        """Convert each PDF page to SVG."""
        
        log.info(f"Converting PDF to page SVGs: {self.pdf_path}")
        
        # Create pages directory
        self.pages_dir.mkdir(parents=True, exist_ok=True)
        log.info(f"Created pages directory: {self.pages_dir}")
        
        # Open PDF
        doc = fitz.open(self.pdf_path)
        total_pages = len(doc)
        log.info(f"Processing {total_pages} pages...")
        
        page_files = []
        
        for page_num in range(total_pages):
            try:
                page = doc[page_num]
                
                # Export page as SVG
                svg_content = page.get_svg_image(matrix=fitz.Identity)
                
                # Save SVG file
                page_filename = f"page_{page_num + 1:03d}.svg"
                page_filepath = self.pages_dir / page_filename
                
                with open(page_filepath, 'w', encoding='utf-8') as f:
                    f.write(svg_content)
                
                # Store relative path for markdown
                rel_path = str(page_filepath.relative_to(self.md_path.parent))
                page_files.append((page_num + 1, rel_path))
                
                log.info(f"Converted page {page_num + 1:3d}/{total_pages} -> {page_filename}")
                
            except Exception as e:
                log.error(f"Failed to convert page {page_num + 1}: {e}")
        
        doc.close()
        log.info(f"✅ Converted {len(page_files)} pages to SVG")
        
        return page_files
    
    def create_markdown_with_pages(self, page_files):
        """Create markdown file with embedded page SVGs."""
        
        log.info(f"Creating markdown file: {self.md_path}")
        
        # Create backup if file exists
        if self.md_path.exists():
            backup_path = self.md_path.with_suffix('.md.backup-before-svg-conversion')
            self.md_path.rename(backup_path)
            log.info(f"Created backup: {backup_path}")
        
        # Build markdown content
        lines = [
            f"# NXP NTAG424 DNA Datasheet",
            "",
            "**Complete datasheet converted to SVG pages for easy reference**",
            "",
            f"- **Total Pages:** {len(page_files)}",
            f"- **Format:** Vector SVG (scalable, searchable)",
            f"- **Source:** {self.pdf_path.name}",
            "",
            "---",
            "",
            "## Table of Contents",
            "",
        ]
        
        # Add basic TOC (we'll enhance this)
        key_sections = [
            (1, "Cover & Overview"),
            (6, "Block Diagram & Pin Configuration"), 
            (9, "File System Structure"),
            (17, "Command Interface"),
            (46, "Authentication Protocols"),
            (62, "Key Management Commands"),
            (77, "ISO Commands"),
            (87, "Specifications"),
        ]
        
        for page_num, description in key_sections:
            if page_num <= len(page_files):
                lines.extend([
                    f"- [Page {page_num}: {description}](#page-{page_num})",
                ])
        
        lines.extend([
            "",
            "---",
            "",
            "## Pages",
            "",
        ])
        
        # Add each page
        for page_num, svg_path in page_files:
            lines.extend([
                f"### Page {page_num}",
                "",
                f"![Page {page_num}]({svg_path})",
                "",
                "---",
                "",
            ])
        
        # Write markdown file
        with open(self.md_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        log.info(f"✅ Created markdown with {len(page_files)} embedded SVG pages")
        
    def convert(self):
        """Run the full conversion process."""
        log.info("Starting PDF to SVG pages conversion...")
        
        # Convert pages to SVG
        page_files = self.convert_pdf_to_pages()
        
        if not page_files:
            log.error("No pages converted successfully!")
            return False
        
        # Create markdown with embedded SVGs
        self.create_markdown_with_pages(page_files)
        
        log.info("🎉 Conversion complete!")
        log.info(f"📄 Markdown file: {self.md_path}")
        log.info(f"📁 SVG pages: {self.pages_dir}")
        log.info(f"🔍 Navigate to specific content using page numbers")
        
        return True

def main():
    """Main function."""
    
    # Check if PDF exists
    pdf_path = "nxp-ntag424-datasheet.pdf"
    if not Path(pdf_path).exists():
        log.error(f"PDF file not found: {pdf_path}")
        return
    
    # Convert PDF to SVG pages
    converter = PDFToSVGConverter(pdf_path)
    success = converter.convert()
    
    if success:
        log.info("✅ Ready to use! The complete datasheet is now available as:")
        log.info("   - High-quality SVG pages (scalable vectors)")
        log.info("   - Easy navigation by page number")
        log.info("   - Perfect for referencing specific protocols/diagrams")

if __name__ == "__main__":
    main()
