#!/usr/bin/env python3
"""
HTML to Markdown Converter with SVG Preservation

This tool converts HTML files to markdown while:
- Preserving embedded SVG content
- Maintaining table structures  
- Keeping formatting clean and readable

Supports both pandoc (if available) and custom conversion.

Usage: python html_to_markdown_converter.py <html_file> [output_name]
"""

import sys
import subprocess
import logging
from pathlib import Path
import re
from typing import Optional
from html.parser import HTMLParser
import html

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

class HTMLToMarkdownConverter(HTMLParser):
    """Custom HTML to Markdown converter that preserves SVGs."""
    
    def __init__(self):
        super().__init__()
        self.output = []
        self.current_tag = None
        self.tag_stack = []
        self.in_svg = False
        self.svg_content = []
        self.in_table = False
        self.table_rows = []
        self.current_row = []
        self.in_cell = False
        self.cell_content = []
        self.in_pre = False
        
    def handle_starttag(self, tag, attrs):
        self.tag_stack.append(tag)
        self.current_tag = tag
        
        if tag == 'svg':
            self.in_svg = True
            self.svg_content = [f'<{tag}']
            for attr, value in attrs:
                self.svg_content.append(f' {attr}="{value}"')
            self.svg_content.append('>')
            
        elif tag == 'table':
            self.in_table = True
            self.table_rows = []
            
        elif tag == 'tr' and self.in_table:
            self.current_row = []
            
        elif tag in ['td', 'th'] and self.in_table:
            self.in_cell = True
            self.cell_content = []
            
        elif tag == 'h1':
            self.output.append('\n# ')
        elif tag == 'h2':
            self.output.append('\n## ')
        elif tag == 'h3':
            self.output.append('\n### ')
        elif tag == 'h4':
            self.output.append('\n#### ')
        elif tag == 'h5':
            self.output.append('\n##### ')
        elif tag == 'h6':
            self.output.append('\n###### ')
        elif tag == 'p':
            self.output.append('\n\n')
        elif tag == 'br':
            self.output.append('\n')
        elif tag == 'hr':
            self.output.append('\n\n---\n\n')
        elif tag == 'strong' or tag == 'b':
            self.output.append('**')
        elif tag == 'em' or tag == 'i':
            self.output.append('*')
        elif tag == 'code':
            self.output.append('`')
        elif tag == 'pre':
            self.in_pre = True
            self.output.append('\n```\n')
        elif tag == 'div' and any(attr[0] == 'class' and 'page' in attr[1] for attr in attrs):
            self.output.append('\n\n')
            
    def handle_endtag(self, tag):
        if self.tag_stack:
            self.tag_stack.pop()
        self.current_tag = self.tag_stack[-1] if self.tag_stack else None
        
        if tag == 'svg' and self.in_svg:
            self.svg_content.append(f'</{tag}>')
            self.output.append('\n\n')
            self.output.append(''.join(self.svg_content))
            self.output.append('\n\n')
            self.in_svg = False
            self.svg_content = []
            
        elif tag == 'table' and self.in_table:
            # Convert collected table data to markdown table
            if self.table_rows:
                self.output.append('\n\n')
                self.output.append(self.format_table_as_markdown())
                self.output.append('\n\n')
            self.in_table = False
            self.table_rows = []
            
        elif tag == 'tr' and self.in_table:
            if self.current_row:
                self.table_rows.append(self.current_row[:])
            self.current_row = []
            
        elif tag in ['td', 'th'] and self.in_table and self.in_cell:
            cell_text = ''.join(self.cell_content).strip()
            self.current_row.append(cell_text)
            self.in_cell = False
            self.cell_content = []
            
        elif tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            self.output.append('\n')
        elif tag == 'p':
            self.output.append('\n')
        elif tag == 'strong' or tag == 'b':
            self.output.append('**')
        elif tag == 'em' or tag == 'i':
            self.output.append('*')
        elif tag == 'code':
            self.output.append('`')
        elif tag == 'pre':
            self.in_pre = False
            self.output.append('\n```\n')
            
    def handle_data(self, data):
        if self.in_svg:
            self.svg_content.append(html.escape(data))
        elif self.in_cell:
            self.cell_content.append(data)
        else:
            # Clean up whitespace but preserve intentional formatting
            if self.in_pre:
                self.output.append(data)
            else:
                # Normalize whitespace but keep structure
                cleaned = re.sub(r'\s+', ' ', data) if data.strip() else data
                if cleaned.strip():  # Only add non-empty content
                    self.output.append(cleaned)
    
    def format_table_as_markdown(self) -> str:
        """Convert table rows to markdown table format."""
        if not self.table_rows:
            return ""
        
        # Determine max columns
        max_cols = max(len(row) for row in self.table_rows)
        
        # Pad all rows to same length
        for row in self.table_rows:
            while len(row) < max_cols:
                row.append("")
        
        lines = []
        
        # Header row (assume first row is header)
        if self.table_rows:
            header = self.table_rows[0]
            lines.append("| " + " | ".join(header) + " |")
            lines.append("| " + " | ".join(["---"] * max_cols) + " |")
            
            # Data rows
            for row in self.table_rows[1:]:
                lines.append("| " + " | ".join(row) + " |")
        
        return "\n".join(lines)
    
    def get_markdown(self) -> str:
        """Get the final markdown content."""
        result = ''.join(self.output)
        
        # Clean up excessive newlines
        result = re.sub(r'\n{4,}', '\n\n\n', result)
        
        # Clean up whitespace around SVG
        result = re.sub(r'\n+(<svg.*?</svg>)\n+', r'\n\n\1\n\n', result, flags=re.DOTALL)
        
        return result.strip()

class HTMLToMarkdownExtractor:
    """Extract HTML to Markdown with SVG preservation."""
    
    def __init__(self, html_path: str, output_name: str = None, use_pandoc: bool = True):
        self.html_path = Path(html_path)
        if not self.html_path.exists():
            raise FileNotFoundError(f"HTML file not found: {html_path}")
            
        # Auto-generate output name
        if output_name is None:
            output_name = self.html_path.stem
            
        self.output_name = output_name
        self.md_path = Path(f"{output_name}.md")
        self.use_pandoc = use_pandoc
        
    def has_pandoc(self) -> bool:
        """Check if pandoc is available."""
        try:
            subprocess.run(['pandoc', '--version'], 
                         capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def convert_with_pandoc(self) -> bool:
        """Convert using pandoc with SVG preservation."""
        try:
            cmd = [
                'pandoc',
                str(self.html_path),
                '-f', 'html',
                '-t', 'markdown',
                '--wrap=none',  # Don't wrap lines
                '--markdown-headings=atx',  # Use # style headings
                '-o', str(self.md_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                log.info("✅ Converted using pandoc")
                return True
            else:
                log.warning(f"Pandoc failed: {result.stderr}")
                return False
                
        except Exception as e:
            log.warning(f"Pandoc conversion failed: {e}")
            return False
    
    def convert_with_custom_parser(self) -> bool:
        """Convert using custom HTML parser."""
        try:
            # Read HTML content
            with open(self.html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Parse with custom converter
            converter = HTMLToMarkdownConverter()
            converter.feed(html_content)
            
            # Get markdown result
            markdown_content = converter.get_markdown()
            
            # Write markdown file
            with open(self.md_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            log.info("✅ Converted using custom parser")
            return True
            
        except Exception as e:
            log.error(f"Custom conversion failed: {e}")
            return False
    
    def convert(self) -> bool:
        """Convert HTML to markdown."""
        log.info(f"Converting HTML to Markdown: {self.html_path}")
        
        # Create backup if file exists
        if self.md_path.exists():
            backup_path = self.md_path.with_suffix('.md.backup')
            self.md_path.rename(backup_path)
            log.info(f"Created backup: {backup_path}")
        
        # Try pandoc first if requested and available
        if self.use_pandoc and self.has_pandoc():
            log.info("Using pandoc for conversion...")
            if self.convert_with_pandoc():
                return True
            else:
                log.info("Pandoc failed, falling back to custom parser...")
        
        # Use custom parser
        log.info("Using custom HTML parser...")
        return self.convert_with_custom_parser()

def main():
    """Main function."""
    
    if len(sys.argv) < 2:
        print("Usage: python html_to_markdown_converter.py <html_file> [output_name] [--no-pandoc]")
        print("\nFeatures:")
        print("  • Preserves embedded SVG content")
        print("  • Maintains table structures")  
        print("  • Uses pandoc if available, custom parser as fallback")
        print("  • Clean markdown output")
        print("\nOptions:")
        print("  --no-pandoc    Skip pandoc and use custom parser")
        print("\nExample: python html_to_markdown_converter.py acr122u-spec.html")
        return
    
    html_file = sys.argv[1]
    output_name = None
    use_pandoc = True
    
    # Process remaining arguments
    for arg in sys.argv[2:]:
        if arg == '--no-pandoc':
            use_pandoc = False
        elif not arg.startswith('--'):
            output_name = arg
    
    try:
        converter = HTMLToMarkdownExtractor(html_file, output_name, use_pandoc)
        success = converter.convert()
        
        if success:
            log.info("✅ HTML to Markdown conversion successful!")
            log.info(f"📄 Markdown file: {converter.md_path}")
            log.info("🔍 SVG content preserved inline")
            
    except Exception as e:
        log.error(f"Conversion failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
