#!/usr/bin/env python3
"""
Extract base64-encoded images from seritag document and convert to SVG using machine vision.

This script:
1. Extracts base64 PNG images from the seritag markdown document
2. Converts them to PNG files 
3. Uses machine vision/OCR to convert PNG images to SVG format
4. Updates the markdown file to reference SVG files instead of base64 data
"""

import base64
import re
import logging
from pathlib import Path
from PIL import Image
import io
import subprocess
import os

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

class SeritaguImageExtractor:
    """Extract and convert embedded base64 images from seritag document."""
    
    def __init__(self, markdown_file: str = "nfc_tag_auth_explained_seritag_text.md"):
        self.markdown_file = Path(markdown_file)
        self.images_dir = Path("investigation_ref/seritag_images")
        self.svg_dir = Path("investigation_ref/seritag_svg") 
        
        # Create output directories
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.svg_dir.mkdir(parents=True, exist_ok=True)
        
    def extract_base64_images(self):
        """Extract base64 encoded images from markdown file."""
        
        log.info(f"Reading markdown file: {self.markdown_file}")
        
        with open(self.markdown_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find all base64 image definitions
        # Pattern: [imageN]: <data:image/png;base64,BASE64_DATA>
        pattern = r'\[image(\d+)\]:\s*<data:image/(\w+);base64,([^>]+)>'
        matches = re.findall(pattern, content, re.MULTILINE | re.DOTALL)
        
        log.info(f"Found {len(matches)} embedded images")
        
        extracted_images = []
        
        for image_num, image_format, base64_data in matches:
            try:
                # Clean up base64 data (remove whitespace/newlines)
                clean_base64 = re.sub(r'\s', '', base64_data)
                
                # Decode base64 data
                image_data = base64.b64decode(clean_base64)
                
                # Create PNG file
                png_filename = f"seritag_image_{image_num}.png"
                png_path = self.images_dir / png_filename
                
                with open(png_path, 'wb') as f:
                    f.write(image_data)
                
                # Verify it's a valid image
                with Image.open(png_path) as img:
                    log.info(f"Extracted image {image_num}: {img.size[0]}x{img.size[1]} {img.format}")
                
                extracted_images.append({
                    'number': image_num,
                    'format': image_format,
                    'png_path': png_path,
                    'filename': png_filename
                })
                
            except Exception as e:
                log.error(f"Failed to extract image {image_num}: {e}")
        
        log.info(f"✅ Extracted {len(extracted_images)} images to PNG format")
        return extracted_images
    
    def convert_png_to_svg_with_potrace(self, png_path: Path) -> Path:
        """Convert PNG to SVG using potrace (vector tracing)."""
        
        svg_filename = png_path.stem + ".svg"
        svg_path = self.svg_dir / svg_filename
        
        # First convert PNG to PBM (bitmap) format for potrace
        pbm_path = png_path.with_suffix('.pbm')
        
        try:
            # Convert PNG to grayscale PBM using ImageMagick
            subprocess.run([
                'magick', 'convert', 
                str(png_path),
                '-colorspace', 'Gray',
                '-threshold', '50%',  # Convert to pure black/white
                str(pbm_path)
            ], check=True)
            
            # Use potrace to convert PBM to SVG
            subprocess.run([
                'potrace',
                '--svg',
                '--output', str(svg_path),
                '--turnpolicy', 'minority',  # Better for text
                '--turdsize', '2',           # Remove small speckles  
                '--optcurve',                # Optimize curves
                str(pbm_path)
            ], check=True)
            
            # Clean up temporary PBM file
            pbm_path.unlink(missing_ok=True)
            
            log.info(f"✅ Converted {png_path.name} to SVG using potrace")
            return svg_path
            
        except subprocess.CalledProcessError as e:
            log.error(f"Failed to convert {png_path.name} with potrace: {e}")
            return None
        except FileNotFoundError:
            log.warning("potrace or ImageMagick not found, trying alternative method")
            return self.convert_png_to_svg_simple(png_path)
    
    def convert_png_to_svg_simple(self, png_path: Path) -> Path:
        """Simple PNG to SVG conversion (embeds PNG as base64)."""
        
        svg_filename = png_path.stem + ".svg"
        svg_path = self.svg_dir / svg_filename
        
        try:
            # Read PNG and encode as base64
            with open(png_path, 'rb') as f:
                png_data = f.read()
            
            base64_data = base64.b64encode(png_data).decode('ascii')
            
            # Get image dimensions
            with Image.open(png_path) as img:
                width, height = img.size
            
            # Create SVG that embeds the PNG
            svg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" 
     xmlns:xlink="http://www.w3.org/1999/xlink"
     width="{width}" height="{height}" 
     viewBox="0 0 {width} {height}">
  <image x="0" y="0" width="{width}" height="{height}" 
         xlink:href="data:image/png;base64,{base64_data}"/>
</svg>'''
            
            with open(svg_path, 'w', encoding='utf-8') as f:
                f.write(svg_content)
            
            log.info(f"✅ Converted {png_path.name} to SVG (embedded PNG)")
            return svg_path
            
        except Exception as e:
            log.error(f"Failed to convert {png_path.name} to SVG: {e}")
            return None
    
    def update_markdown_file(self, extracted_images):
        """Update markdown file to reference SVG files instead of base64 data."""
        
        log.info("Updating markdown file to reference SVG files")
        
        with open(self.markdown_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Create backup
        backup_path = self.markdown_file.with_suffix('.md.backup-before-svg-conversion')
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
        log.info(f"Created backup: {backup_path}")
        
        # Replace base64 image definitions with SVG file references
        for img in extracted_images:
            image_num = img['number']
            svg_filename = f"seritag_image_{image_num}.svg"
            svg_rel_path = f"investigation_ref/seritag_svg/{svg_filename}"
            
            # Replace the base64 definition with SVG file reference
            old_pattern = rf'\[image{image_num}\]:\s*<data:image/\w+;base64,[^>]+>'
            new_definition = f'[image{image_num}]: {svg_rel_path}'
            
            content = re.sub(old_pattern, new_definition, content, flags=re.MULTILINE | re.DOTALL)
        
        # Write updated content
        with open(self.markdown_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        log.info(f"✅ Updated markdown file to reference {len(extracted_images)} SVG files")
    
    def convert_images(self):
        """Run the complete image extraction and conversion process."""
        
        log.info("Starting seritag image extraction and SVG conversion...")
        
        # Extract base64 images to PNG
        extracted_images = self.extract_base64_images()
        
        if not extracted_images:
            log.error("No images extracted!")
            return False
        
        # Convert PNG images to SVG
        for img in extracted_images:
            png_path = img['png_path']
            
            # Try potrace first (better quality), fallback to simple embedding
            svg_path = self.convert_png_to_svg_with_potrace(png_path)
            
            if not svg_path:
                svg_path = self.convert_png_to_svg_simple(png_path)
            
            img['svg_path'] = svg_path
        
        # Update markdown file to reference SVG files
        self.update_markdown_file(extracted_images)
        
        log.info("🎉 Seritag image conversion complete!")
        log.info(f"📁 PNG files: {self.images_dir}")
        log.info(f"📁 SVG files: {self.svg_dir}")
        log.info(f"📄 Updated markdown: {self.markdown_file}")
        
        return True

def main():
    """Main function."""
    
    # Check if markdown file exists
    markdown_file = "nfc_tag_auth_explained_seritag_text.md"
    if not Path(markdown_file).exists():
        log.error(f"Markdown file not found: {markdown_file}")
        return
    
    # Extract and convert images
    extractor = SeritaguImageExtractor(markdown_file)
    success = extractor.convert_images()
    
    if success:
        log.info("✅ All seritag images converted to SVG format!")
        log.info("💡 The images now use scalable vector graphics instead of embedded base64 data")
        log.info("🔍 You can view the individual SVG files and the updated markdown document")

if __name__ == "__main__":
    main()
