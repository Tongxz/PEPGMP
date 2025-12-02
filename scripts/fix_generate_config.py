#!/usr/bin/env python3
# Fix generate_production_config.sh syntax errors

import re

filepath = 'scripts/generate_production_config.sh'

# Read file
with open(filepath, 'rb') as f:
    content = f.read()

# Decode with error handling
try:
    lines = content.decode('utf-8').split('\n')
except:
    lines = content.decode('utf-8', errors='ignore').split('\n')

# Fix broken echo statements
fixed_lines = []
for i, line in enumerate(lines):
    # Fix line 33
    if '鉁?宸插' in line or '已备份' in line:
        if 'echo' in line:
            line = '    echo "✓ 已备份现有配置文件"'
    
    # Fix line 177
    if '鈿狅笍' in line or '⚠️' in line:
        if 'echo -e' in line and '${YELLOW}' in line:
            line = 'echo -e "${YELLOW}⚠️  请将以上信息保存到密码管理器！${NC}"'
    
    # Ensure all echo statements with variables have proper quotes
    if 'echo -e' in line and '${' in line:
        # Check if quotes are balanced
        single_quotes = line.count("'")
        double_quotes = line.count('"')
        # If quotes are unbalanced, try to fix
        if double_quotes % 2 != 0:
            # Try to find and fix the issue
            if line.endswith('{NC}"') or line.endswith('{NC}\'"'):
                # Already fixed
                pass
            elif not line.endswith('"'):
                line = line.rstrip() + '"'
    
    fixed_lines.append(line)

# Join lines
text = '\n'.join(fixed_lines)

# Ensure file ends with newline
if not text.endswith('\n'):
    text += '\n'

# Write back
with open(filepath, 'wb') as f:
    f.write(text.encode('utf-8'))

print("Fixed generate_production_config.sh")
print("Please test in WSL: bash scripts/generate_production_config.sh")
