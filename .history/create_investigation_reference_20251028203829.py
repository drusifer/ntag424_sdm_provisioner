#!/usr/bin/env python3
"""
Create a focused investigation reference with only the key pages needed for Seritag analysis.

This extracts specific pages that are relevant to authentication, commands, and troubleshooting.
"""

import fitz  # PyMuPDF
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

class InvestigationReference:
    """Create focused reference documentation for specific investigation needs."""
    
    def __init__(self):
        self.output_dir = Path("investigation_ref")
        self.output_dir.mkdir(exist_ok=True)
        
    def extract_key_pages(self, pdf_path: str, page_specs: list, output_name: str):
        """Extract specific pages and create focused reference.
        
        Args:
            pdf_path: Path to source PDF
            page_specs: List of (page_num, description) tuples
            output_name: Name for output files
        """
        
        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            log.error(f"PDF not found: {pdf_path}")
            return []
        
        log.info(f"Extracting key pages from: {pdf_file.name}")
        
        doc = fitz.open(pdf_file)
        extracted_pages = []
        
        for page_num, description in page_specs:
            try:
                # PDF pages are 0-indexed, but we specify 1-indexed
                page = doc[page_num - 1]
                
                # Export as SVG
                svg_content = page.get_svg_image(matrix=fitz.Identity)
                
                # Save SVG
                filename = f"{output_name}_page_{page_num:02d}.svg"
                filepath = self.output_dir / filename
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(svg_content)
                
                extracted_pages.append((page_num, description, filepath))
                log.info(f"  Page {page_num:2d}: {description}")
                
            except Exception as e:
                log.error(f"Failed to extract page {page_num}: {e}")
        
        doc.close()
        return extracted_pages
        
    def create_investigation_guide(self):
        """Create the complete investigation reference."""
        
        log.info("Creating Seritag Investigation Reference...")
        
        # Key NXP NTAG424 pages for investigation
        nxp_pages = [
            (17, "Command Structure & APDU Format"),
            (45, "Status Words (SW1/SW2) - Error Codes"), 
            (46, "AuthenticateEV2First Protocol - What Seritag Modifies"),
            (49, "AuthenticateEV2NonFirst Protocol"),
            (62, "ChangeKey Command Protocol"),
            (6, "IC Block Diagram"),
            (9, "File System Structure"),
        ]
        
        # Key ACR122U reader pages
        acr122u_pages = [
            (8, "APDU Command Structure"),
            (13, "PC/SC Command Interface"),
            (15, "Authentication Commands"),
            (18, "Error Handling & Status"),
            (25, "Direct Commands to PICC"),
        ]
        
        # Extract pages
        nxp_extracted = self.extract_key_pages("nxp-ntag424-datasheet.pdf", nxp_pages, "ntag424")
        acr122u_extracted = self.extract_key_pages("API-ACR122U-2.04.pdf", acr122u_pages, "acr122u")
        
        # Create markdown reference
        self.create_markdown_reference(nxp_extracted, acr122u_extracted)
        
    def create_markdown_reference(self, nxp_pages, acr122u_pages):
        """Create focused markdown reference guide."""
        
        md_path = self.output_dir / "seritag_investigation_reference.md"
        
        lines = [
            "# Seritag Investigation Reference",
            "",
            "**Focused reference for analyzing Seritag NTAG424 DNA modified firmware**",
            "",
            "This reference contains only the key pages needed to understand:",
            "- Standard NXP NTAG424 authentication protocols",
            "- ACR122U reader APDU interface", 
            "- Status codes and error handling",
            "- Command structure for comparison with Seritag behavior",
            "",
            "---",
            "",
            "## 🎯 Quick Reference",
            "",
            "### Key Findings So Far:",
            "- **Seritag EV2 Phase 1**: ✅ Works (standard)",
            "- **Seritag EV2 Phase 2**: ❌ Fails (modified protocol)",
            "- **Command 0x51**: Returns `91CA` (Wrong Session State) - Seritag-specific",
            "- **Standard Commands**: Most return `911C` (Command Not Supported)",
            "",
            "### Investigation Status:",
            "- [x] Confirmed Phase 1 authentication works",
            "- [x] Identified Phase 2 protocol modification", 
            "- [x] Found Seritag-specific command 0x51",
            "- [ ] **Next**: Analyze Phase 2 differences using reference below",
            "- [ ] **Goal**: Exploit command 0x51 to reset/reconfigure tags",
            "",
            "---",
            "",
            "## 📖 NXP NTAG424 DNA Specification",
            "",
        ]
        
        # Add NXP pages
        for page_num, description, filepath in nxp_pages:
            rel_path = filepath.name
            lines.extend([
                f"### Page {page_num}: {description}",
                "",
                f"![NXP Page {page_num}]({rel_path})",
                "",
                "---",
                "",
            ])
        
        lines.extend([
            "## 📡 ACR122U Reader API Specification",
            "",
        ])
        
        # Add ACR122U pages  
        for page_num, description, filepath in acr122u_pages:
            rel_path = filepath.name
            lines.extend([
                f"### Page {page_num}: {description}",
                "",
                f"![ACR122U Page {page_num}]({rel_path})",
                "", 
                "---",
                "",
            ])
        
        lines.extend([
            "## 🔍 Investigation Notes",
            "",
            "### Status Word Reference (NXP Page 45)",
            "- `9000`: Success",
            "- `91AF`: Additional frame expected", 
            "- `91AE`: Authentication error",
            "- `91CA`: Wrong session state ← **Seritag command 0x51 returns this**",
            "- `911C`: Command not supported",
            "- `6A80`: Wrong parameters",
            "- `6985`: Command not allowed",
            "",
            "### Seritag Behavior Analysis",
            "1. **Standard EV2 Phase 1** (NXP Page 46) - Works normally",
            "2. **Modified EV2 Phase 2** - Seritag uses different protocol",
            "3. **Command 0x51** - Seritag-specific, requires full auth (91CA when not authenticated)",
            "",
            "### Next Investigation Steps",
            "- [ ] Compare actual Seritag Phase 2 response with NXP spec",
            "- [ ] Try command 0x51 after successful Phase 1+2 auth", 
            "- [ ] Analyze 0x51 parameter requirements",
            "- [ ] Test if 0x51 can reset chip to standard NXP behavior",
            "",
        ])
        
        # Write reference file
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
            
        log.info(f"✅ Created investigation reference: {md_path}")
        log.info(f"📁 SVG files in: {self.output_dir}")
        
def main():
    """Main function."""
    ref = InvestigationReference()
    ref.create_investigation_guide()
    
    log.info("🎯 Focused reference created!")
    log.info("   - Much smaller and faster to navigate")
    log.info("   - Contains only pages relevant to Seritag investigation")
    log.info("   - Includes investigation notes and status tracking")

if __name__ == "__main__":
    main()
