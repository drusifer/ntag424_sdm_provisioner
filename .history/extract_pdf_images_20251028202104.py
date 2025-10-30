#!/usr/bin/env python3
"""
Extract images from NXP NTAG424 datasheet PDF and update markdown with local image URLs.

This script:
1. Extracts all images from the PDF
2. Creates a local images directory
3. Updates the markdown file to reference local images
4. Maps figure references to actual images
"""

import re
import os
import logging
from pathlib import Path
from typing import Dict, List, Tuple

# Try importing PDF processing libraries
try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

class PDFImageExtractor:
    def __init__(self, pdf_path: str, md_path: str):
        self.pdf_path = Path(pdf_path)
        self.md_path = Path(md_path)
        self.images_dir = self.md_path.parent / "images" / "nxp-datasheet"
        self.extracted_images: Dict[int, str] = {}
        
    def create_images_directory(self):
        """Create the images directory structure."""
        self.images_dir.mkdir(parents=True, exist_ok=True)
        log.info(f"Created images directory: {self.images_dir}")
        
    def extract_images_with_pymupdf(self) -> Dict[int, str]:
        """Extract images using PyMuPDF."""
        if not HAS_PYMUPDF:
            log.error("PyMuPDF not installed. Install with: pip install PyMuPDF")
            return {}
            
        log.info("Extracting images using PyMuPDF...")
        doc = fitz.open(self.pdf_path)
        extracted_images = {}
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            image_list = page.get_images()
            
            log.info(f"Page {page_num + 1}: Found {len(image_list)} images")
            
            for img_index, img in enumerate(image_list):
                xref = img[0]  # xref number
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                
                # Create filename
                filename = f"page_{page_num + 1:03d}_img_{img_index + 1:02d}.{image_ext}"
                filepath = self.images_dir / filename
                
                # Save image
                with open(filepath, "wb") as f:
                    f.write(image_bytes)
                    
                # Store mapping
                image_key = f"{page_num}_{img_index}"
                extracted_images[image_key] = str(filepath.relative_to(self.md_path.parent))
                
                log.info(f"Extracted: {filename} ({len(image_bytes)} bytes)")
                
        doc.close()
        return extracted_images
        
    def find_figure_references(self) -> List[Tuple[int, str, str]]:
        """Find figure references in the markdown file."""
        log.info("Analyzing markdown for figure references...")
        
        with open(self.md_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Patterns to match figure references
        patterns = [
            (r'Figure (\d+)\.?\s*([^|]*?)(?:\s*\*[a-z]+-\d+\*)?', 'figure'),
            (r'Table (\d+)\.?\s*([^|]*?)(?:\s*\*[a-z]+-\d+\*)?', 'table'),
            (r'\*([a-z]+-\d+)\*', 'reference_id'),
        ]
        
        references = []
        for pattern, ref_type in patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                line_start = content.rfind('\n', 0, match.start()) + 1
                line_num = content.count('\n', 0, line_start) + 1
                
                if ref_type == 'reference_id':
                    references.append((line_num, ref_type, match.group(1)))
                else:
                    number = match.group(1)
                    title = match.group(2).strip() if len(match.groups()) > 1 else ""
                    references.append((line_num, f"{ref_type}_{number}", title))
                    
        log.info(f"Found {len(references)} figure/table references")
        return references
        
    def create_image_mapping(self, references: List[Tuple[int, str, str]]) -> Dict[str, str]:
        """Create mapping between figure references and extracted images."""
        log.info("Creating image mapping...")
        
        # For now, create a simple mapping based on order
        # In a real implementation, you'd need to analyze the PDF structure
        # to match specific figures to their references
        
        image_mapping = {}
        
        # Get list of extracted images
        if self.images_dir.exists():
            image_files = sorted([f for f in self.images_dir.glob("*.png") if f.is_file()])
            image_files.extend(sorted([f for f in self.images_dir.glob("*.jpg") if f.is_file()]))
            image_files.extend(sorted([f for f in self.images_dir.glob("*.jpeg") if f.is_file()]))
            
            # Create mapping for figures
            figure_refs = [ref for ref in references if ref[1].startswith('figure_')]
            for i, (line_num, ref_id, title) in enumerate(figure_refs):
                if i < len(image_files):
                    rel_path = str(image_files[i].relative_to(self.md_path.parent))
                    image_mapping[ref_id] = rel_path
                    log.info(f"Mapped {ref_id} -> {rel_path}")
                    
        return image_mapping
        
    def update_markdown_with_images(self, image_mapping: Dict[str, str]):
        """Update the markdown file to include image references."""
        log.info("Updating markdown file with image references...")
        
        with open(self.md_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Create backup
        backup_path = self.md_path.with_suffix('.md.backup')
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
        log.info(f"Created backup: {backup_path}")
        
        # Replace figure references with image tags
        updated_content = content
        
        for ref_id, image_path in image_mapping.items():
            if ref_id.startswith('figure_'):
                figure_num = ref_id.split('_')[1]
                
                # Pattern to match the figure reference
                pattern = rf'(Figure {figure_num}\.?\s*[^|]*?)(?:\s*\*[a-z]+-\d+\*)?'
                
                def replace_with_image(match):
                    original_text = match.group(1)
                    return f'{original_text}\n\n![Figure {figure_num}]({image_path})\n'
                
                updated_content = re.sub(pattern, replace_with_image, updated_content, flags=re.IGNORECASE)
                
        # Write updated content
        with open(self.md_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)
            
        log.info("Markdown file updated with image references")
        
    def extract_and_update(self):
        """Main method to extract images and update markdown."""
        log.info(f"Processing PDF: {self.pdf_path}")
        log.info(f"Updating markdown: {self.md_path}")
        
        # Create directory
        self.create_images_directory()
        
        # Extract images
        if HAS_PYMUPDF:
            self.extracted_images = self.extract_images_with_pymupdf()
        else:
            log.error("No PDF processing library available!")
            log.info("Install PyMuPDF with: pip install PyMuPDF")
            return False
            
        # Find references
        references = self.find_figure_references()
        
        # Create mapping
        image_mapping = self.create_image_mapping(references)
        
        # Update markdown
        if image_mapping:
            self.update_markdown_with_images(image_mapping)
            
        log.info("✅ PDF image extraction and markdown update complete!")
        return True

def main():
    """Main function."""
    pdf_path = "nxp-ntag424-datasheet.pdf"
    md_path = "nxp-ntag424-datasheet.md"
    
    if not os.path.exists(pdf_path):
        log.error(f"PDF file not found: {pdf_path}")
        return
        
    if not os.path.exists(md_path):
        log.error(f"Markdown file not found: {md_path}")
        return
        
    extractor = PDFImageExtractor(pdf_path, md_path)
    extractor.extract_and_update()

if __name__ == "__main__":
    main()
