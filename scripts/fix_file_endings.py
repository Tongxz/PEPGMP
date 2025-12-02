#!/usr/bin/env python3
# Fix file endings and ensure files end with newline

import os
import sys

def fix_file(filepath):
    """Fix line endings and ensure file ends with newline."""
    try:
        # Read file in binary mode
        with open(filepath, 'rb') as f:
            content = f.read()
        
        # Remove all \r characters (CRLF -> LF)
        content = content.replace(b'\r\n', b'\n').replace(b'\r', b'\n')
        
        # Ensure file ends with newline
        if not content.endswith(b'\n'):
            content += b'\n'
        
        # Write back in binary mode
        with open(filepath, 'wb') as f:
            f.write(content)
        
        print(f"Fixed: {filepath}")
        return True
    except Exception as e:
        print(f"Error fixing {filepath}: {e}", file=sys.stderr)
        return False

if __name__ == '__main__':
    scripts = [
        'scripts/generate_production_config.sh',
        'scripts/prepare_minimal_deploy.sh',
        'scripts/start_prod_wsl.sh',
        'scripts/fix_line_endings.sh',
        'scripts/fix_line_endings_wsl.sh',
    ]
    
    for script in scripts:
        if os.path.exists(script):
            fix_file(script)
        else:
            print(f"Not found: {script}")

