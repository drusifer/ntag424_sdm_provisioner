#!/usr/bin/env python3
"""
Fix Windows backslash paths in markdown image links.

Convert backslashes to forward slashes in markdown image references.
"""

import re
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

def fix_markdown_image_paths(md_path: str):
    """Fix image paths in markdown file by converting backslashes to forward slashes."""
    
    md_file = Path(md_path)
    log.info(f"Fixing image paths in: {md_file}")
    
    # Read the markdown file
    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all image references with backslashes
    # Pattern: ![Something](path\with\backslashes.svg)
    pattern = r'!\[([^\]]*)\]\(([^)]*\\[^)]*)\)'
    
    matches = list(re.finditer(pattern, content))
    log.info(f"Found {len(matches)} image links with backslashes")
    
    if not matches:
        log.info("No backslash paths found - already fixed!")
        return
    
    # Create backup first
    backup_path = md_file.with_suffix('.md.backup-paths')
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    log.info(f"Created backup: {backup_path}")
    
    # Fix all backslash paths
    def fix_path(match):
        alt_text = match.group(1)
        original_path = match.group(2)
        fixed_path = original_path.replace('\\', '/')
        
        log.info(f"Fixed: {original_path} -> {fixed_path}")
        return f'![{alt_text}]({fixed_path})'
    
    # Apply fixes
    fixed_content = re.sub(pattern, fix_path, content)
    
    # Write the fixed content
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    
    log.info(f"✅ Fixed {len(matches)} image paths in markdown file")

def main():
    """Main function."""
    md_path = "nxp-ntag424-datasheet.md"
    fix_markdown_image_paths(md_path)

if __name__ == "__main__":
    main()
