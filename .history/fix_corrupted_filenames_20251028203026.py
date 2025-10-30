#!/usr/bin/env python3
"""
Fix corrupted filenames in the markdown image links.

The previous regex replacement corrupted the filenames.
"""

import re
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

def fix_corrupted_filenames(md_path: str):
    """Fix corrupted filenames in image links."""
    
    md_file = Path(md_path)
    log.info(f"Fixing corrupted filenames in: {md_file}")
    
    # Read the markdown file
    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Create backup first
    backup_path = md_file.with_suffix('.md.backup-corrupted')
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    log.info(f"Created backup: {backup_path}")
    
    # Fix corrupted filenames
    fixes_applied = 0
    
    # Fix "figure	able_X" -> "table_X" (tab character corruption)
    pattern1 = r'(!\[[^]]*\]\(images/nxp-datasheet/)figure\table_(\d+_page_\d+\.svg\))'
    replacement1 = r'\1table_\2'
    matches1 = re.findall(pattern1, content)
    if matches1:
        log.info(f"Fixing {len(matches1)} 'figure\\table_' corruptions")
        content = re.sub(pattern1, replacement1, content)
        fixes_applied += len(matches1)
    
    # Fix "figureigure_X" -> "figure_X" (double figure)
    pattern2 = r'(!\[[^]]*\]\(images/nxp-datasheet/)figureigure_(\d+_page_\d+\.svg\))'
    replacement2 = r'\1figure_\2'
    matches2 = re.findall(pattern2, content)
    if matches2:
        log.info(f"Fixing {len(matches2)} 'figureigure_' corruptions")
        content = re.sub(pattern2, replacement2, content)
        fixes_applied += len(matches2)
    
    # Fix "figureX_able_Y" -> "table_Y" (figure prefix on tables)
    pattern3 = r'(!\[Table [^]]*\]\(images/nxp-datasheet/)figure[^t]*able_(\d+_page_\d+\.svg\))'
    replacement3 = r'\1table_\2'
    matches3 = re.findall(pattern3, content)
    if matches3:
        log.info(f"Fixing {len(matches3)} 'figure*able_' corruptions (tables)")
        content = re.sub(pattern3, replacement3, content)
        fixes_applied += len(matches3)
    
    # More aggressive fix for remaining corruption - manually fix known patterns
    manual_fixes = [
        # Fix tab characters and other corruption
        (r'figure\table_', 'table_'),
        (r'figureigure_', 'figure_'),
        (r'figure\s+able_', 'table_'),
        (r'figure[^tf]*able_', 'table_'),
    ]
    
    for pattern, replacement in manual_fixes:
        old_content = content
        content = re.sub(pattern, replacement, content)
        if content != old_content:
            count = len(re.findall(pattern, old_content))
            log.info(f"Applied manual fix: {pattern} -> {replacement} ({count} matches)")
            fixes_applied += count
    
    if fixes_applied > 0:
        # Write the fixed content
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        log.info(f"✅ Fixed {fixes_applied} corrupted filenames")
    else:
        log.info("No corrupted filenames found to fix")

def main():
    """Main function."""
    md_path = "nxp-ntag424-datasheet.md"
    fix_corrupted_filenames(md_path)

if __name__ == "__main__":
    main()
