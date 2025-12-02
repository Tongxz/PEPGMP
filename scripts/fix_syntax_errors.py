#!/usr/bin/env python3
# Fix syntax errors in prepare_minimal_deploy.sh

filepath = 'scripts/prepare_minimal_deploy.sh'

with open(filepath, 'rb') as f:
    content = f.read()

text = content.decode('utf-8', errors='ignore')
lines = text.split('\n')

# Fix line 68 and similar issues
for i, line in enumerate(lines, 1):
    # Fix default parameter values with Chinese characters
    if 'local description="${3:-' in line and '鏂囦欢' in line:
        lines[i-1] = '    local description="${3:-file}"'
    elif 'local description="${3:-' in line and '鐩綍' in line:
        lines[i-1] = '    local description="${3:-directory}"'
    
    # Fix echo statements with problematic characters
    if 'echo "○ Skipped:' in line and '(' in line:
        # Ensure proper quoting
        if '$description' in line:
            lines[i-1] = '        echo "○ Skipped: $description (file exists and identical)"'
    
    # Fix any unclosed quotes or parentheses in echo statements
    if line.strip().startswith('echo ') and line.count('"') % 2 != 0:
        # Try to fix unclosed quotes
        if not line.rstrip().endswith('"'):
            lines[i-1] = line.rstrip() + '"'

# Join lines back
text = '\n'.join(lines)

# Ensure file ends with newline
if not text.endswith('\n'):
    text += '\n'

with open(filepath, 'wb') as f:
    f.write(text.encode('utf-8'))

print("Fixed syntax errors in prepare_minimal_deploy.sh")

