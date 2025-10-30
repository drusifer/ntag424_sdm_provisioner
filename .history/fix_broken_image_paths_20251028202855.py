#!/usr/bin/env python3
"""
Fix broken image paths in the markdown file.

The paths got split across lines and mangled. This script fixes them.
"""

import re
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

def fix_broken_image_paths(md_path: str):
    """Fix broken image paths that got split across lines."""
    
    md_file = Path(md_path)
    log.info(f"Fixing broken image paths in: {md_file}")
    
    # Read the markdown file
    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Create backup first
    backup_path = md_file.with_suffix('.md.backup-broken-paths')
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    log.info(f"Created backup: {backup_path}")
    
    # Pattern to match broken image links like:
    # ![Figure 1](images
    # xp-datasheetigure_1_page_006.svg)
    
    # First, let's fix the obvious pattern where the path got mangled
    patterns_to_fix = [
        # Fix the specific broken pattern we saw
        (r'!\[([^\]]+)\]\(images\s*\n\s*xp-datasheet([^)]*\.svg)\)', r'![\1](images/nxp-datasheet/figure\2)'),
        # Fix other potential broken patterns
        (r'!\[([^\]]+)\]\(images\s*\n\s*([^)]*\.svg)\)', r'![\1](images/nxp-datasheet/\2)'),
        # Fix paths that might have backslashes
        (r'!\[([^\]]+)\]\(([^)]*\\[^)]*\.svg)\)', lambda m: f'![{m.group(1)}]({m.group(2).replace(chr(92), "/")})'),
    ]
    
    fixed_content = content
    total_fixes = 0
    
    for pattern, replacement in patterns_to_fix:
        if callable(replacement):
            # Handle lambda function replacements
            matches = list(re.finditer(pattern, fixed_content))
            for match in matches:
                old_text = match.group(0)
                new_text = replacement(match)
                fixed_content = fixed_content.replace(old_text, new_text, 1)
                log.info(f"Fixed: {old_text} -> {new_text}")
                total_fixes += 1
        else:
            # Handle string replacements
            matches = list(re.finditer(pattern, fixed_content))
            if matches:
                log.info(f"Found {len(matches)} matches for pattern: {pattern}")
                for match in matches:
                    log.info(f"  Match: {match.group(0)}")
                
                fixed_content = re.sub(pattern, replacement, fixed_content)
                total_fixes += len(matches)
    
    # Alternative approach: Look for specific broken patterns manually
    if total_fixes == 0:
        log.info("No regex matches found, trying manual fixes...")
        
        # Look for the specific broken pattern we observed
        lines = fixed_content.split('\n')
        i = 0
        while i < len(lines) - 1:
            current_line = lines[i].strip()
            next_line = lines[i + 1].strip()
            
            # Look for ![Figure X](images followed by mangled path
            if current_line.startswith('![') and '](images' in current_line and not current_line.endswith('.svg)'):
                if next_line.endswith('.svg)'):
                    # This is a broken image link
                    figure_part = current_line.split('](images')[0] + ']'
                    path_part = next_line
                    
                    # Try to reconstruct the correct path
                    if 'igure_' in path_part:  # "figure" got mangled to "igure"
                        # Extract the figure number and page
                        path_clean = path_part.replace('xp-datasheet', '').replace('igure_', 'figure_')
                        correct_path = f"images/nxp-datasheet/{path_clean}"
                        
                        # Create the correct image link
                        fixed_link = f"{figure_part}({correct_path}"
                        
                        log.info(f"Fixed broken image link:")
                        log.info(f"  From: {current_line}")
                        log.info(f"        {next_line}")
                        log.info(f"  To:   {fixed_link}")
                        
                        # Replace both lines with the fixed single line
                        lines[i] = fixed_link
                        lines[i + 1] = ""  # Empty the next line
                        total_fixes += 1
            
            i += 1
        
        if total_fixes > 0:
            fixed_content = '\n'.join(lines)
    
    if total_fixes > 0:
        # Write the fixed content
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        
        log.info(f"✅ Fixed {total_fixes} broken image paths")
    else:
        log.info("No broken image paths found to fix")

def main():
    """Main function."""
    md_path = "nxp-ntag424-datasheet.md"
    fix_broken_image_paths(md_path)

if __name__ == "__main__":
    main()
