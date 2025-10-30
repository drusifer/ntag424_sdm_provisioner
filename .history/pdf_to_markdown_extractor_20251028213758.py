#!/usr/bin/env python3
"""
Enhanced PDF to Markdown Extractor with Mermaid Diagrams

This tool extracts PDFs to markdown format with:
- Text extraction for PDFs with extractable text
- OCR for image-based PDFs 
- Automatic table conversion to markdown tables
- Mermaid diagram generation for flowcharts and diagrams
- PNG extraction for complex images
- Intelligent content analysis and formatting

Usage: python pdf_to_markdown_extractor.py <pdf_file> [output_name]
"""

import sys
import fitz  # PyMuPDF
import logging
from pathlib import Path
import re
import json
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
import base64

# Try to import optional dependencies
try:
    import pytesseract
    HAS_OCR = True
except ImportError:
    HAS_OCR = False
    print("Warning: pytesseract not available - OCR features disabled")

try:
    from PIL import Image
    import io
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("Warning: PIL not available - image processing features disabled")

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

@dataclass
class ExtractedContent:
    """Container for extracted content from a PDF page."""
    page_num: int
    text: str
    images: List[Dict[str, Any]]
    tables: List[List[List[str]]]
    has_text: bool
    needs_ocr: bool
    diagrams: List[Dict[str, Any]]

class EnhancedPDFExtractor:
    """Enhanced PDF extractor that creates markdown with mermaid diagrams."""
    
    def __init__(self, pdf_path: str, output_name: str = None, use_inline_svg: bool = True):
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
            
        # Auto-generate output name from PDF filename if not provided
        if output_name is None:
            output_name = self.pdf_path.stem
            
        self.output_name = output_name
        self.use_inline_svg = use_inline_svg
        self.images_dir = Path(f"images/{output_name}")
        self.md_path = Path(f"{output_name}-extracted.md")
        
        # Check capabilities
        self.has_ocr = HAS_OCR
        self.has_pil = HAS_PIL
        
    def analyze_page_content(self, page: fitz.Page, page_num: int) -> ExtractedContent:
        """Analyze a PDF page and extract structured content."""
        
        # Extract text
        text = page.get_text()
        has_meaningful_text = len(text.strip()) > 10 and not self._is_mostly_gibberish(text)
        
        # Extract images
        images = []
        image_list = page.get_images()
        
        for img_index, img in enumerate(image_list):
            try:
                # Get image data
                xref = img[0]
                pix = fitz.Pixmap(page.parent, xref)
                
                if pix.n - pix.alpha < 4:  # GRAY or RGB
                    img_data = {
                        'index': img_index,
                        'xref': xref,
                        'width': pix.width,
                        'height': pix.height,
                        'colorspace': pix.colorspace.name if pix.colorspace else 'unknown',
                        'size_bytes': len(pix.pil_tobytes('PNG')) if self.has_pil else 0
                    }
                    images.append(img_data)
                
                pix = None  # Free memory
            except Exception as e:
                log.warning(f"Failed to analyze image {img_index} on page {page_num}: {e}")
        
        # Extract tables (basic heuristic)
        tables = self._extract_tables_from_text(text)
        
        # Detect diagrams/flowcharts (heuristic based on text patterns)
        diagrams = self._detect_diagrams(text, page)
        
        # Determine if OCR is needed
        needs_ocr = not has_meaningful_text and len(images) > 0
        
        return ExtractedContent(
            page_num=page_num,
            text=text,
            images=images,
            tables=tables,
            has_text=has_meaningful_text,
            needs_ocr=needs_ocr,
            diagrams=diagrams
        )
    
    def _is_mostly_gibberish(self, text: str) -> bool:
        """Check if text is mostly unreadable characters."""
        if not text.strip():
            return True
        
        # If text is very short, be more lenient
        if len(text.strip()) < 20:
            return False
        
        # Count readable vs unreadable characters - be more permissive
        readable_chars = sum(1 for c in text if c.isalnum() or c.isspace() or c in '.,;!?-()[]{}/@#$%^&*+=|\\<>:"\'')
        total_chars = len(text)
        
        # Lower threshold - allow more special characters
        return (readable_chars / total_chars) < 0.5 if total_chars > 0 else True
    
    def _extract_tables_from_text(self, text: str) -> List[List[List[str]]]:
        """Extract tables from text using heuristics."""
        tables = []
        
        # Look for patterns that suggest tabular data
        lines = text.split('\n')
        current_table = []
        
        for line in lines:
            # Simple heuristic: lines with multiple whitespace-separated columns
            if re.search(r'\s{2,}.*\s{2,}', line) and len(line.split()) >= 3:
                columns = re.split(r'\s{2,}', line.strip())
                current_table.append(columns)
            else:
                if len(current_table) >= 2:  # At least 2 rows for a table
                    tables.append(current_table)
                current_table = []
        
        # Don't forget the last table
        if len(current_table) >= 2:
            tables.append(current_table)
        
        return tables
    
    def _detect_diagrams(self, text: str, page: fitz.Page) -> List[Dict[str, Any]]:
        """Detect potential diagrams and flowcharts."""
        diagrams = []
        
        # Look for flowchart keywords
        flowchart_keywords = [
            'flowchart', 'flow chart', 'process flow', 'workflow', 'state machine',
            'algorithm', 'procedure', 'step', 'decision', 'branch', 'loop'
        ]
        
        text_lower = text.lower()
        for keyword in flowchart_keywords:
            if keyword in text_lower:
                diagrams.append({
                    'type': 'flowchart',
                    'keyword': keyword,
                    'confidence': 0.7
                })
                break
        
        # Look for sequence diagram keywords
        sequence_keywords = [
            'sequence', 'interaction', 'message', 'request', 'response',
            'client', 'server', 'authentication', 'protocol'
        ]
        
        for keyword in sequence_keywords:
            if keyword in text_lower:
                diagrams.append({
                    'type': 'sequence',
                    'keyword': keyword,
                    'confidence': 0.6
                })
                break
        
        # Look for network/architecture diagrams
        arch_keywords = [
            'architecture', 'topology', 'network', 'infrastructure',
            'components', 'modules', 'layers', 'stack'
        ]
        
        for keyword in arch_keywords:
            if keyword in text_lower:
                diagrams.append({
                    'type': 'architecture',
                    'keyword': keyword,
                    'confidence': 0.6
                })
                break
        
        return diagrams
    
    def extract_page_as_inline_svg(self, page: fitz.Page, content: ExtractedContent) -> str:
        """Extract page as inline SVG content."""
        
        try:
            # Get page as SVG
            svg_content = page.get_svg_image(matrix=fitz.Identity)
            
            # Clean up SVG for inline embedding
            # Remove XML declaration and add some basic styling
            svg_content = re.sub(r'<\?xml[^>]*\?>\s*', '', svg_content)
            
            # Add some basic responsive styling
            if '<svg' in svg_content and 'style=' not in svg_content:
                svg_content = svg_content.replace('<svg', '<svg style="max-width: 100%; height: auto;"', 1)
            
            log.info(f"Extracted page {content.page_num} as inline SVG ({len(svg_content)} chars)")
            return svg_content
            
        except Exception as e:
            log.error(f"Failed to extract page {content.page_num} as SVG: {e}")
            return ""
    
    def extract_page_images_as_png(self, page: fitz.Page, content: ExtractedContent) -> List[str]:
        """Extract images from page as PNG files."""
        
        image_files = []
        
        if not content.images:
            return image_files
        
        # Create images directory
        self.images_dir.mkdir(parents=True, exist_ok=True)
        
        for img_data in content.images:
            try:
                xref = img_data['xref']
                pix = fitz.Pixmap(page.parent, xref)
                
                if pix.n - pix.alpha < 4:  # GRAY or RGB
                    # Generate filename
                    img_filename = f"page_{content.page_num:03d}_img_{img_data['index']:02d}.png"
                    img_filepath = self.images_dir / img_filename
                    
                    # Save as PNG
                    pix.save(img_filepath)
                    
                    # Store relative path
                    rel_path = str(img_filepath.relative_to(self.md_path.parent))
                    image_files.append(rel_path)
                    
                    log.info(f"Extracted image: {img_filename} ({img_data['width']}x{img_data['height']})")
                
                pix = None  # Free memory
                
            except Exception as e:
                log.error(f"Failed to extract image {img_data['index']} from page {content.page_num}: {e}")
        
        return image_files
    
    def perform_ocr_on_page(self, page: fitz.Page) -> str:
        """Perform OCR on a page image."""
        
        if not self.has_ocr or not self.has_pil:
            log.warning("OCR not available - skipping text extraction")
            return ""
        
        try:
            # Convert page to image
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x scaling for better OCR
            img_data = pix.tobytes("png")
            
            # Use PIL to create image
            img = Image.open(io.BytesIO(img_data))
            
            # Perform OCR
            ocr_text = pytesseract.image_to_string(img, config='--psm 6')
            
            pix = None  # Free memory
            
            return ocr_text.strip()
        
        except Exception as e:
            log.error(f"OCR failed: {e}")
            return ""
    
    def convert_table_to_markdown(self, table: List[List[str]]) -> str:
        """Convert a table to markdown format."""
        
        if not table or len(table) < 2:
            return ""
        
        # Assume first row is header
        header = table[0]
        rows = table[1:]
        
        # Create markdown table
        md_lines = []
        
        # Header row
        md_lines.append("| " + " | ".join(header) + " |")
        
        # Separator row
        md_lines.append("| " + " | ".join(["---"] * len(header)) + " |")
        
        # Data rows
        for row in rows:
            # Pad row to match header length
            padded_row = row + [""] * (len(header) - len(row))
            md_lines.append("| " + " | ".join(padded_row[:len(header)]) + " |")
        
        return "\n".join(md_lines)
    
    def generate_mermaid_diagram(self, diagram_info: Dict[str, Any], text_context: str) -> str:
        """Generate mermaid diagram based on detected diagram type."""
        
        diagram_type = diagram_info.get('type', 'flowchart')
        
        if diagram_type == 'flowchart':
            return self._generate_flowchart_mermaid(text_context)
        elif diagram_type == 'sequence':
            return self._generate_sequence_mermaid(text_context)
        elif diagram_type == 'architecture':
            return self._generate_architecture_mermaid(text_context)
        else:
            return self._generate_generic_diagram_mermaid(text_context)
    
    def _generate_flowchart_mermaid(self, text: str) -> str:
        """Generate a flowchart mermaid diagram."""
        
        # Extract steps and decisions from text
        lines = text.split('\n')
        
        steps = []
        decisions = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Look for numbered steps
            if re.match(r'^\d+\.?\s+', line):
                step = re.sub(r'^\d+\.?\s+', '', line)
                steps.append(step)
            
            # Look for decision-like language
            elif any(word in line.lower() for word in ['if', 'check', 'verify', 'decide', 'choose']):
                decisions.append(line)
        
        # Generate mermaid flowchart
        mermaid_lines = ["```mermaid", "flowchart TD"]
        
        # Add steps
        for i, step in enumerate(steps[:5]):  # Limit to 5 steps
            node_id = f"A{i+1}"
            mermaid_lines.append(f"    {node_id}[{step[:30]}...]")
            if i > 0:
                mermaid_lines.append(f"    A{i} --> A{i+1}")
        
        # Add decisions
        for i, decision in enumerate(decisions[:2]):  # Limit to 2 decisions
            node_id = f"D{i+1}"
            mermaid_lines.append(f"    {node_id}{{{decision[:25]}...}}")
        
        mermaid_lines.append("```")
        
        return "\n".join(mermaid_lines)
    
    def _generate_sequence_mermaid(self, text: str) -> str:
        """Generate a sequence diagram."""
        
        # Look for actors/participants
        actors = set()
        interactions = []
        
        lines = text.split('\n')
        for line in lines:
            # Look for common sequence patterns
            if ' -> ' in line or ' sends ' in line or ' receives ' in line:
                # Extract potential actors
                words = line.split()
                for word in words:
                    if word.lower() in ['client', 'server', 'user', 'system', 'application']:
                        actors.add(word.title())
        
        # Generate mermaid sequence diagram
        mermaid_lines = ["```mermaid", "sequenceDiagram"]
        
        # Add participants
        for actor in sorted(actors):
            mermaid_lines.append(f"    participant {actor}")
        
        # Add basic interactions if we have actors
        if len(actors) >= 2:
            actor_list = sorted(actors)
            mermaid_lines.append(f"    {actor_list[0]} ->> {actor_list[1]}: Request")
            mermaid_lines.append(f"    {actor_list[1]} -->> {actor_list[0]}: Response")
        
        mermaid_lines.append("```")
        
        return "\n".join(mermaid_lines)
    
    def _generate_architecture_mermaid(self, text: str) -> str:
        """Generate an architecture diagram."""
        
        # Look for components
        components = set()
        lines = text.split('\n')
        
        for line in lines:
            words = line.split()
            for word in words:
                if word.lower() in ['module', 'component', 'layer', 'service', 'api', 'database']:
                    components.add(word.title())
        
        # Generate mermaid graph
        mermaid_lines = ["```mermaid", "graph TB"]
        
        # Add components
        for i, comp in enumerate(sorted(components)):
            mermaid_lines.append(f"    {chr(65+i)}[{comp}]")
        
        # Add basic connections
        if len(components) >= 2:
            mermaid_lines.append("    A --> B")
        
        mermaid_lines.append("```")
        
        return "\n".join(mermaid_lines)
    
    def _generate_generic_diagram_mermaid(self, text: str) -> str:
        """Generate a generic diagram."""
        
        return """```mermaid
graph TD
    A[Start] --> B[Process]
    B --> C[End]
```"""
    
    def process_page(self, page: fitz.Page, page_num: int) -> str:
        """Process a single page and return markdown content."""
        
        log.info(f"Processing page {page_num}...")
        
        # Analyze page content
        content = self.analyze_page_content(page, page_num)
        
        # Build markdown for this page
        md_lines = [f"## Page {page_num}\n"]
        
        # Extract text content - prioritize readable text, use OCR only as last resort
        text_content = ""
        if content.has_text:
            # Use extractable text - preserve formatting better
            text_content = content.text
        elif content.needs_ocr:
            # Only use OCR if text extraction completely failed
            log.info(f"Page {page_num} needs OCR - no extractable text found")
            text_content = self.perform_ocr_on_page(page)
            if not text_content:
                log.warning(f"Page {page_num}: OCR also failed")
        
        # Add text content with better formatting preservation
        if text_content:
            # Preserve original formatting better - minimal cleanup
            cleaned_text = re.sub(r'\n\s*\n\s*\n\s*\n', '\n\n\n', text_content)  # Limit to max 3 newlines
            # Don't normalize whitespace too aggressively - preserve indentation
            cleaned_text = re.sub(r'[ \t]{4,}', '    ', cleaned_text)  # Convert excessive tabs/spaces to 4 spaces
            md_lines.append(cleaned_text)
        
        # Add tables only if they're clearly structured
        if content.tables and len(content.tables) > 0:
            md_lines.append("\n")
            for i, table in enumerate(content.tables):
                table_md = self.convert_table_to_markdown(table)
                if table_md:
                    md_lines.append(table_md)
                    md_lines.append("")
        
        # Add mermaid diagrams only for clearly identifiable process flows
        if content.diagrams and any(d['confidence'] > 0.7 for d in content.diagrams):
            md_lines.append("\n")
            for i, diagram in enumerate(content.diagrams):
                if diagram['confidence'] > 0.7:  # Only high-confidence diagrams
                    mermaid_diagram = self.generate_mermaid_diagram(diagram, text_content)
                    md_lines.append(mermaid_diagram)
                    md_lines.append("")
        
        # Handle page visualization - use inline SVG only for graphic-heavy pages
        if self.use_inline_svg:
            # Only use full page SVG for pages that are primarily graphics (no readable text + has images)
            if not content.has_text and len(content.images) > 0:
                md_lines.append("\n### Visual Content\n")
                svg_content = self.extract_page_as_inline_svg(page, content)
                if svg_content:
                    md_lines.append(svg_content)
                    md_lines.append("")
                else:
                    md_lines.append("*Failed to extract page as SVG*\n")
        
        # Extract and reference images as PNGs if not using inline SVG or as fallback
        if content.images and (not self.use_inline_svg or not text_content):
            image_files = self.extract_page_images_as_png(page, content)
            if image_files:
                md_lines.append("\n### Extracted Images\n")
                for i, img_path in enumerate(image_files):
                    md_lines.append(f"#### Image {i+1}\n")
                    md_lines.append(f"![Page {page_num} Image {i+1}]({img_path})\n")
        
        md_lines.append("\n---\n")
        
        return "\n".join(md_lines)
    
    def extract(self):
        """Run the full extraction process."""
        
        log.info(f"Starting enhanced PDF extraction: {self.pdf_path}")
        log.info(f"OCR available: {self.has_ocr}")
        log.info(f"Image processing available: {self.has_pil}")
        
        # Open PDF
        doc = fitz.open(self.pdf_path)
        total_pages = len(doc)
        
        # Get metadata
        metadata = doc.metadata
        title = metadata.get('title', self.pdf_path.stem)
        author = metadata.get('author', 'Unknown')
        subject = metadata.get('subject', '')
        
        log.info(f"Processing {total_pages} pages...")
        
        # Create backup if file exists
        if self.md_path.exists():
            backup_path = self.md_path.with_suffix('.md.backup-before-extraction')
            self.md_path.rename(backup_path)
            log.info(f"Created backup: {backup_path}")
        
        # Build markdown content
        extraction_method = "Text + OCR + " + ("Inline SVG" if self.use_inline_svg else "PNG images")
        features = "Mermaid diagrams, Markdown tables, " + ("Inline SVG" if self.use_inline_svg else "PNG images")
        
        md_lines = [
            f"# {title}",
            "",
            f"**{subject}**" if subject else "**Extracted and Enhanced PDF Content**",
            "",
            f"- **Author:** {author}",
            f"- **Total Pages:** {total_pages}",
            f"- **Extraction Method:** {extraction_method}",
            f"- **Enhanced Features:** {features}",
            f"- **Source:** {self.pdf_path.name}",
            "",
            "---",
            "",
        ]
        
        # Process each page
        for page_num in range(total_pages):
            try:
                page = doc[page_num]
                page_content = self.process_page(page, page_num + 1)
                md_lines.append(page_content)
                
                if (page_num + 1) % 5 == 0 or page_num == 0:
                    log.info(f"Processed page {page_num + 1}/{total_pages}")
                    
            except Exception as e:
                log.error(f"Failed to process page {page_num + 1}: {e}")
                md_lines.append(f"## Page {page_num + 1}\n\n**Error processing page:** {str(e)}\n\n---\n")
        
        # Write markdown file
        with open(self.md_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(md_lines))
        
        doc.close()
        
        log.info("🎉 Enhanced extraction complete!")
        log.info(f"📄 Enhanced markdown: {self.md_path}")
        if self.images_dir.exists():
            log.info(f"🖼️  Extracted images: {self.images_dir}")
        log.info(f"✨ Features: Text extraction, OCR, mermaid diagrams, tables, images")
        
        return True

def main():
    """Main function."""
    
    if len(sys.argv) < 2:
        print("Usage: python pdf_to_markdown_extractor.py <pdf_file> [output_name] [--no-inline-svg]")
        print("\nFeatures:")
        print("  • Text extraction for readable PDFs")
        print("  • OCR for image-based PDFs (requires pytesseract)")
        print("  • Automatic table conversion to markdown")
        print("  • Mermaid diagram generation")
        print("  • Inline SVG embedding (default) or PNG image extraction")
        print("\nOptions:")
        print("  --no-inline-svg    Extract images as PNG files instead of inline SVG")
        print("\nExamples:")
        print("  python pdf_to_markdown_extractor.py API-ACR122U-2.04.pdf acr122u-spec")
        print("  python pdf_to_markdown_extractor.py datasheet.pdf --no-inline-svg")
        return
    
    # Parse arguments
    pdf_file = sys.argv[1]
    output_name = None
    use_inline_svg = True
    
    # Process remaining arguments
    for arg in sys.argv[2:]:
        if arg == '--no-inline-svg':
            use_inline_svg = False
        elif not arg.startswith('--'):
            output_name = arg
    
    try:
        extractor = EnhancedPDFExtractor(pdf_file, output_name, use_inline_svg=use_inline_svg)
        success = extractor.extract()
        
        if success:
            log.info("✅ Enhanced extraction successful!")
            if use_inline_svg:
                log.info("🔍 Check the markdown file for structured content with inline SVG and mermaid diagrams")
            else:
                log.info("🔍 Check the markdown file for structured content with PNG images and mermaid diagrams")
            
    except Exception as e:
        log.error(f"Extraction failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
