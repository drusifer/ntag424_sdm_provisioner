#!/usr/bin/env python3
"""
PDF to HTML Extractor with Embedded SVGs

This tool extracts PDFs to HTML format with:
- Preserved text formatting and layout
- Embedded SVG graphics for complex content
- Table structure preservation
- All formatting maintained

Usage: python pdf_to_html_extractor.py <pdf_file> [output_name]
"""

import sys
import fitz  # PyMuPDF
import logging
from pathlib import Path
import re
import base64
from typing import List, Dict, Tuple, Optional

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

class PDFToHTMLExtractor:
    """Extract PDF to HTML with embedded SVGs and preserved formatting."""
    
    def __init__(self, pdf_path: str, output_name: str = None):
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
            
        # Auto-generate output name from PDF filename if not provided
        if output_name is None:
            output_name = self.pdf_path.stem
            
        self.output_name = output_name
        self.html_path = Path(f"{output_name}.html")
        
    def extract_to_html(self):
        """Extract PDF to HTML with embedded SVGs."""
        
        log.info(f"Starting PDF to HTML extraction: {self.pdf_path}")
        
        # Open PDF
        doc = fitz.open(self.pdf_path)
        total_pages = len(doc)
        
        # Get metadata
        metadata = doc.metadata
        title = metadata.get('title', self.pdf_path.stem)
        author = metadata.get('author', 'Unknown')
        
        log.info(f"Processing {total_pages} pages...")
        
        # Create backup if file exists
        if self.html_path.exists():
            backup_path = self.html_path.with_suffix('.html.backup')
            self.html_path.rename(backup_path)
            log.info(f"Created backup: {backup_path}")
        
        # Build HTML content
        html_parts = []
        
        # HTML header with styling
        html_parts.append(f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: 'Times New Roman', serif;
            line-height: 1.4;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #fff;
        }}
        .page {{
            margin-bottom: 40px;
            padding: 20px;
            border: 1px solid #ddd;
            background-color: #fafafa;
        }}
        .page-header {{
            font-size: 14px;
            color: #666;
            margin-bottom: 15px;
            border-bottom: 1px solid #eee;
            padding-bottom: 10px;
        }}
        .text-content {{
            white-space: pre-wrap;
            font-family: inherit;
            font-size: 12px;
            line-height: 1.3;
        }}
        .svg-content {{
            margin: 20px 0;
            text-align: center;
        }}
        .svg-content svg {{
            max-width: 100%;
            height: auto;
            border: 1px solid #ddd;
        }}
        table {{
            border-collapse: collapse;
            margin: 10px 0;
            width: 100%;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }}
        th {{
            background-color: #f5f5f5;
        }}
        .mixed-content {{
            margin: 15px 0;
        }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <p><strong>Author:</strong> {author}</p>
    <p><strong>Pages:</strong> {total_pages}</p>
    <hr>
''')
        
        # Process each page
        for page_num in range(total_pages):
            try:
                page = doc[page_num]
                page_content = self.process_page_to_html(page, page_num + 1)
                html_parts.append(page_content)
                
                if (page_num + 1) % 10 == 0 or page_num == 0:
                    log.info(f"Processed page {page_num + 1}/{total_pages}")
                    
            except Exception as e:
                log.error(f"Failed to process page {page_num + 1}: {e}")
                html_parts.append(f'''
    <div class="page">
        <div class="page-header">Page {page_num + 1} - Error</div>
        <p><em>Error processing page: {str(e)}</em></p>
    </div>
''')
        
        # HTML footer
        html_parts.append('''
</body>
</html>''')
        
        # Write HTML file
        with open(self.html_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(html_parts))
        
        doc.close()
        
        log.info("🎉 HTML extraction complete!")
        log.info(f"📄 HTML file: {self.html_path}")
        log.info(f"✨ Features: Preserved formatting, embedded SVGs, table structures")
        
        return True
    
    def process_page_to_html(self, page: fitz.Page, page_num: int) -> str:
        """Process a single page to HTML content."""
        
        # Try to get HTML directly from PyMuPDF
        try:
            # Get page text with formatting
            text_content = page.get_text()
            
            # Get page as SVG for complex layouts
            svg_content = page.get_svg_image(matrix=fitz.Identity)
            
            # Clean up SVG for embedding
            svg_content = re.sub(r'<\?xml[^>]*\?>\s*', '', svg_content)
            svg_content = re.sub(r'<!DOCTYPE[^>]*>\s*', '', svg_content)
            
            # Check if page has meaningful text vs graphics
            has_substantial_text = len(text_content.strip()) > 50
            
            html_parts = [f'''
    <div class="page" id="page-{page_num}">
        <div class="page-header">Page {page_num}</div>''']
            
            if has_substantial_text:
                # Page has readable text - use text content with SVG as backup
                
                # Try to detect and preserve tables
                if self.has_table_structure(text_content):
                    table_html = self.convert_text_to_table_html(text_content)
                    if table_html:
                        html_parts.append(f'''
        <div class="mixed-content">
            {table_html}
        </div>''')
                    else:
                        # Fallback to preformatted text
                        escaped_text = self.escape_html(text_content)
                        html_parts.append(f'''
        <div class="text-content">{escaped_text}</div>''')
                else:
                    # Regular text content
                    escaped_text = self.escape_html(text_content)
                    html_parts.append(f'''
        <div class="text-content">{escaped_text}</div>''')
                
                # Add SVG for any graphics/diagrams
                if self.page_has_graphics(page):
                    html_parts.append(f'''
        <div class="svg-content">
            {svg_content}
        </div>''')
            else:
                # Page is primarily graphics - use SVG
                html_parts.append(f'''
        <div class="svg-content">
            {svg_content}
        </div>''')
            
            html_parts.append('    </div>')
            
            return '\n'.join(html_parts)
            
        except Exception as e:
            log.error(f"Failed to process page {page_num}: {e}")
            return f'''
    <div class="page">
        <div class="page-header">Page {page_num} - Processing Error</div>
        <p><em>Could not process page content</em></p>
    </div>'''
    
    def has_table_structure(self, text: str) -> bool:
        """Detect if text contains table-like structure."""
        lines = text.split('\n')
        
        # Look for lines with multiple columns separated by whitespace
        table_lines = 0
        for line in lines:
            if re.search(r'\S+\s{2,}\S+\s{2,}\S+', line):  # At least 3 columns
                table_lines += 1
        
        return table_lines >= 3  # At least 3 table-like lines
    
    def convert_text_to_table_html(self, text: str) -> str:
        """Convert text with table structure to HTML table."""
        lines = text.split('\n')
        table_lines = []
        
        for line in lines:
            if re.search(r'\S+\s{2,}\S+', line):  # Has column structure
                # Split on multiple whitespace
                columns = re.split(r'\s{2,}', line.strip())
                if len(columns) >= 2:
                    table_lines.append(columns)
        
        if len(table_lines) < 2:
            return ""
        
        # Build HTML table
        html_parts = ['<table>']
        
        # First row as header if it looks like headers
        first_row = table_lines[0]
        if any(word.lower() in ['name', 'value', 'type', 'description', 'parameter', 'field'] 
               for word in first_row):
            html_parts.append('<thead><tr>')
            for col in first_row:
                html_parts.append(f'<th>{self.escape_html(col)}</th>')
            html_parts.append('</tr></thead>')
            data_rows = table_lines[1:]
        else:
            data_rows = table_lines
        
        # Data rows
        html_parts.append('<tbody>')
        for row in data_rows:
            html_parts.append('<tr>')
            for col in row:
                html_parts.append(f'<td>{self.escape_html(col)}</td>')
            html_parts.append('</tr>')
        html_parts.append('</tbody>')
        
        html_parts.append('</table>')
        
        return '\n'.join(html_parts)
    
    def page_has_graphics(self, page: fitz.Page) -> bool:
        """Check if page has graphics/images."""
        images = page.get_images()
        drawings = page.get_drawings()
        return len(images) > 0 or len(drawings) > 0
    
    def escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('"', '&quot;')
        text = text.replace("'", '&#x27;')
        return text

def main():
    """Main function."""
    
    if len(sys.argv) < 2:
        print("Usage: python pdf_to_html_extractor.py <pdf_file> [output_name]")
        print("\nFeatures:")
        print("  • Preserves original formatting and layout")
        print("  • Embeds SVG graphics directly in HTML")
        print("  • Maintains table structures")
        print("  • Readable text with selectable content")
        print("\nExample: python pdf_to_html_extractor.py API-ACR122U-2.04.pdf acr122u-spec")
        return
    
    pdf_file = sys.argv[1]
    output_name = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        extractor = PDFToHTMLExtractor(pdf_file, output_name)
        success = extractor.extract_to_html()
        
        if success:
            log.info("✅ HTML extraction successful!")
            log.info("🔍 Next step: Convert HTML to markdown using pandoc or html2text")
            
    except Exception as e:
        log.error(f"Extraction failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
