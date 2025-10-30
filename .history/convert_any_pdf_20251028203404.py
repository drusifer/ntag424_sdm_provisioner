#!/usr/bin/env python3
"""
Convert any PDF to page-by-page SVGs with markdown navigation.

Usage: python convert_any_pdf.py <pdf_file> [output_name]
"""

import sys
import fitz  # PyMuPDF
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

class GenericPDFConverter:
    """Convert any PDF to page-by-page SVGs with markdown."""
    
    def __init__(self, pdf_path: str, output_name: str = None):
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
            
        # Auto-generate output name from PDF filename if not provided
        if output_name is None:
            output_name = self.pdf_path.stem
            
        self.output_name = output_name
        self.pages_dir = Path(f"pages/{output_name}")
        self.md_path = Path(f"{output_name}.md")
        
    def convert_pdf_to_pages(self):
        """Convert each PDF page to SVG."""
        
        log.info(f"Converting PDF: {self.pdf_path}")
        
        # Create pages directory
        self.pages_dir.mkdir(parents=True, exist_ok=True)
        log.info(f"Created pages directory: {self.pages_dir}")
        
        # Open PDF and get basic info
        doc = fitz.open(self.pdf_path)
        total_pages = len(doc)
        
        # Try to extract title and basic info
        metadata = doc.metadata
        title = metadata.get('title', self.pdf_path.stem)
        author = metadata.get('author', 'Unknown')
        subject = metadata.get('subject', '')
        
        log.info(f"PDF Info:")
        log.info(f"  Title: {title}")
        log.info(f"  Author: {author}")
        log.info(f"  Subject: {subject}")
        log.info(f"  Pages: {total_pages}")
        
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
                
                if (page_num + 1) % 10 == 0 or page_num == 0 or page_num == total_pages - 1:
                    log.info(f"Converted page {page_num + 1:3d}/{total_pages}")
                
            except Exception as e:
                log.error(f"Failed to convert page {page_num + 1}: {e}")
        
        doc.close()
        log.info(f"✅ Converted {len(page_files)} pages to SVG")
        
        return page_files, {
            'title': title,
            'author': author,
            'subject': subject,
            'total_pages': total_pages
        }
    
    def create_markdown_with_pages(self, page_files, metadata):
        """Create markdown file with embedded page SVGs."""
        
        log.info(f"Creating markdown: {self.md_path}")
        
        # Create backup if file exists
        if self.md_path.exists():
            backup_path = self.md_path.with_suffix('.md.backup-before-conversion')
            self.md_path.rename(backup_path)
            log.info(f"Created backup: {backup_path}")
        
        # Build markdown content
        title = metadata['title']
        author = metadata['author']
        subject = metadata['subject']
        
        lines = [
            f"# {title}",
            "",
            f"**{subject}**" if subject else "**Complete documentation converted to SVG pages**",
            "",
            f"- **Author:** {author}",
            f"- **Total Pages:** {len(page_files)}",
            f"- **Format:** Vector SVG (scalable, searchable)",
            f"- **Source:** {self.pdf_path.name}",
            "",
            "---",
            "",
            "## Quick Navigation",
            "",
            "Jump to any page by clicking the links below:",
            "",
        ]
        
        # Create page index (10 pages per row)
        for i in range(0, len(page_files), 10):
            page_range = page_files[i:i+10]
            page_links = [f"[{p[0]}](#page-{p[0]})" for p in page_range]
            lines.append(f"**Pages {page_range[0][0]}-{page_range[-1][0]}:** {' • '.join(page_links)}")
        
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
                f"<a id=\"page-{page_num}\"></a>",
                f"## Page {page_num}",
                "",
                f"![Page {page_num}]({svg_path})",
                "",
                f"[🔝 Back to top](#quick-navigation)",
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
        log.info("Starting PDF to SVG conversion...")
        
        # Convert pages to SVG
        page_files, metadata = self.convert_pdf_to_pages()
        
        if not page_files:
            log.error("No pages converted successfully!")
            return False
        
        # Create markdown with embedded SVGs
        self.create_markdown_with_pages(page_files, metadata)
        
        log.info("🎉 Conversion complete!")
        log.info(f"📄 Markdown: {self.md_path}")
        log.info(f"📁 SVG pages: {self.pages_dir}")
        
        return True

def main():
    """Main function."""
    
    if len(sys.argv) < 2:
        print("Usage: python convert_any_pdf.py <pdf_file> [output_name]")
        print("Example: python convert_any_pdf.py API-ACR122U-2.04.pdf acr122u-spec")
        return
    
    pdf_file = sys.argv[1]
    output_name = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        converter = GenericPDFConverter(pdf_file, output_name)
        success = converter.convert()
        
        if success:
            log.info("✅ Conversion successful!")
            log.info("🔍 Use the markdown file to navigate and reference content easily")
            
    except Exception as e:
        log.error(f"Conversion failed: {e}")

if __name__ == "__main__":
    main()
