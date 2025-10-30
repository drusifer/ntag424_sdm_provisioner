#!/usr/bin/env python3
"""
Enhanced PDF graphics extraction for NXP NTAG424 datasheet.

Since the PDF contains vector graphics instead of raster images,
this script will:
1. Render PDF pages as images
2. Crop regions containing figures/tables
3. Create image files for markdown embedding
"""

import re
import os
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import fitz  # PyMuPDF
from PIL import Image

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

class PDFGraphicsExtractor:
    def __init__(self, pdf_path: str, md_path: str):
        self.pdf_path = Path(pdf_path)
        self.md_path = Path(md_path)
        self.images_dir = self.md_path.parent / "images" / "nxp-datasheet"
        self.dpi = 150  # Resolution for rendering
        
    def create_images_directory(self):
        """Create the images directory structure."""
        self.images_dir.mkdir(parents=True, exist_ok=True)
        log.info(f"Created images directory: {self.images_dir}")
        
    def find_figure_pages(self) -> Dict[str, int]:
        """Find which pages contain specific figures by analyzing text."""
        log.info("Analyzing PDF text to find figure locations...")
        
        doc = fitz.open(self.pdf_path)
        figure_pages = {}
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            
            # Look for figure references
            figure_matches = re.finditer(r'Figure (\d+)\.?\s*([^.\n]*)', text, re.IGNORECASE)
            for match in figure_matches:
                figure_num = match.group(1)
                figure_title = match.group(2).strip()
                figure_id = f"figure_{figure_num}"
                
                if figure_id not in figure_pages:
                    figure_pages[figure_id] = page_num
                    log.info(f"Found {figure_id} on page {page_num + 1}: {figure_title}")
                    
            # Look for table references  
            table_matches = re.finditer(r'Table (\d+)\.?\s*([^.\n]*)', text, re.IGNORECASE)
            for match in table_matches:
                table_num = match.group(1)
                table_title = match.group(2).strip()
                table_id = f"table_{table_num}"
                
                if table_id not in figure_pages:
                    figure_pages[table_id] = page_num
                    log.info(f"Found {table_id} on page {page_num + 1}: {table_title}")
                    
        doc.close()
        return figure_pages
        
    def extract_specific_figures(self, figure_pages: Dict[str, int]) -> Dict[str, str]:
        """Extract specific figures by rendering and cropping pages."""
        log.info("Extracting figures by rendering PDF pages...")
        
        doc = fitz.open(self.pdf_path)
        extracted_figures = {}
        
        # Known important figures based on common datasheet structure
        priority_figures = [
            "figure_1",  # Block diagram
            "figure_2",  # Pin configuration  
            "figure_3",  # File system
            "table_1",   # Ordering info
            "table_2",   # Quick reference
            "table_3",   # Pin allocation
        ]
        
        # Extract priority figures first
        for fig_id in priority_figures:
            if fig_id in figure_pages:
                page_num = figure_pages[fig_id]
                image_path = self.render_page_as_image(doc, page_num, fig_id)
                if image_path:
                    extracted_figures[fig_id] = image_path
                    
        # Extract other figures
        for fig_id, page_num in figure_pages.items():
            if fig_id not in extracted_figures:
                image_path = self.render_page_as_image(doc, page_num, fig_id)
                if image_path:
                    extracted_figures[fig_id] = image_path
                    
        doc.close()
        return extracted_figures
        
    def render_page_as_svg(self, doc: fitz.Document, page_num: int, fig_id: str) -> Optional[str]:
        """Export a PDF page as SVG vector graphics."""
        try:
            page = doc[page_num]
            
            # Export page as SVG
            svg_content = page.get_svg_image(matrix=fitz.Identity)
            
            # Save as SVG
            filename = f"{fig_id}_page_{page_num + 1:03d}.svg"
            filepath = self.images_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(svg_content)
            
            rel_path = str(filepath.relative_to(self.md_path.parent))
            log.info(f"Exported {fig_id} -> {filename} (SVG)")
            
            return rel_path
            
        except Exception as e:
            log.error(f"Failed to export {fig_id} on page {page_num + 1} as SVG: {e}")
            return None
            
    def render_page_as_image(self, doc: fitz.Document, page_num: int, fig_id: str) -> Optional[str]:
        """Render a PDF page as an image (fallback if SVG fails)."""
        try:
            page = doc[page_num]
            
            # Render page to high-quality image
            mat = fitz.Matrix(self.dpi / 72, self.dpi / 72)  # Scale matrix
            pix = page.get_pixmap(matrix=mat)
            
            # Save as PNG
            filename = f"{fig_id}_page_{page_num + 1:03d}.png"
            filepath = self.images_dir / filename
            
            pix.save(str(filepath))
            
            rel_path = str(filepath.relative_to(self.md_path.parent))
            log.info(f"Rendered {fig_id} -> {filename} (PNG fallback)")
            
            return rel_path
            
        except Exception as e:
            log.error(f"Failed to render {fig_id} on page {page_num + 1}: {e}")
            return None
            
    def create_manual_figure_mapping(self) -> Dict[str, str]:
        """Create manual mapping for known figures when auto-detection fails."""
        log.info("Creating manual figure mapping...")
        
        # Manual mapping based on typical NXP datasheet structure
        manual_mapping = {
            "figure_1": "Block diagram (usually page 6-8)",
            "figure_2": "Pin configuration (usually page 8-10)", 
            "figure_3": "File system diagram (usually page 12-15)",
            "table_1": "Ordering information (usually page 4-6)",
            "table_2": "Quick reference data (usually page 5-7)",
            "table_3": "Pin allocation table (usually page 9-11)",
        }
        
        # Try to render these pages
        doc = fitz.open(self.pdf_path)
        extracted = {}
        
        # Look for specific content patterns
        for page_num in range(min(20, len(doc))):  # Check first 20 pages
            page = doc[page_num]
            text = page.get_text().lower()
            
            # Block diagram keywords
            if any(word in text for word in ["block diagram", "analog digital", "cpu mmu", "aes-128"]):
                if "figure_1" not in extracted:
                    path = self.render_page_as_image(doc, page_num, "figure_1")
                    if path:
                        extracted["figure_1"] = path
                        
            # Pin configuration
            if any(word in text for word in ["pin configuration", "sot500", "moa8", "la lb"]):
                if "figure_2" not in extracted:
                    path = self.render_page_as_image(doc, page_num, "figure_2")
                    if path:
                        extracted["figure_2"] = path
                        
            # File system
            if any(word in text for word in ["file system", "picc/mf level", "ndef file", "cc file"]):
                if "figure_3" not in extracted:
                    path = self.render_page_as_image(doc, page_num, "figure_3")
                    if path:
                        extracted["figure_3"] = path
                        
        doc.close()
        return extracted
        
    def update_markdown_with_figures(self, figure_mapping: Dict[str, str]):
        """Update markdown file with figure images."""
        log.info("Updating markdown with figure references...")
        
        with open(self.md_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Create backup
        backup_path = self.md_path.with_suffix('.md.backup')
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
        log.info(f"Created backup: {backup_path}")
        
        # Update content
        updated_content = content
        
        for fig_id, image_path in figure_mapping.items():
            if fig_id.startswith('figure_'):
                figure_num = fig_id.split('_')[1]
                # Look for the figure reference and add image after it
                pattern = rf'(Figure {figure_num}\.?[^\n]*\n)'
                replacement = rf'\1\n![Figure {figure_num}]({image_path})\n'
                updated_content = re.sub(pattern, replacement, updated_content, flags=re.IGNORECASE)
                log.info(f"Added image for Figure {figure_num}")
                
            elif fig_id.startswith('table_'):
                table_num = fig_id.split('_')[1]
                # Look for the table reference and add image after it
                pattern = rf'(Table {table_num}\.?[^\n]*\n)'
                replacement = rf'\1\n![Table {table_num}]({image_path})\n'
                updated_content = re.sub(pattern, replacement, updated_content, flags=re.IGNORECASE)
                log.info(f"Added image for Table {table_num}")
                
        # Write updated content
        with open(self.md_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)
            
        log.info("Markdown updated with figure images")
        
    def extract_and_update(self):
        """Main extraction method."""
        log.info(f"Processing PDF with vector graphics: {self.pdf_path}")
        
        self.create_images_directory()
        
        # Try to find figures by text analysis
        figure_pages = self.find_figure_pages()
        
        if figure_pages:
            log.info(f"Found {len(figure_pages)} figures/tables in PDF text")
            extracted_figures = self.extract_specific_figures(figure_pages)
        else:
            log.info("No figures found by text analysis, using manual mapping")
            extracted_figures = self.create_manual_figure_mapping()
            
        if extracted_figures:
            log.info(f"Extracted {len(extracted_figures)} figures")
            self.update_markdown_with_figures(extracted_figures)
            
            # List what was extracted
            log.info("Extracted figures:")
            for fig_id, path in extracted_figures.items():
                log.info(f"  {fig_id}: {path}")
        else:
            log.warning("No figures could be extracted")
            
        log.info("✅ PDF graphics extraction complete!")

def main():
    """Main function."""
    pdf_path = "nxp-ntag424-datasheet.pdf"
    md_path = "nxp-ntag424-datasheet.md"
    
    extractor = PDFGraphicsExtractor(pdf_path, md_path)
    extractor.extract_and_update()

if __name__ == "__main__":
    main()
