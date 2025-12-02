#!/usr/bin/env python3
# Convert Chinese prompts to English in generate_production_config.sh

filepath = 'scripts/generate_production_config.sh'

# Read file
with open(filepath, 'rb') as f:
    content = f.read()

# Decode
try:
    text = content.decode('utf-8')
except:
    text = content.decode('utf-8', errors='ignore')

# Add locale setting at the beginning (after shebang)
if 'export LANG' not in text:
    lines = text.split('\n')
    # Find the line after shebang and color definitions
    insert_pos = 0
    for i, line in enumerate(lines):
        if line.startswith('set -e'):
            insert_pos = i + 1
            break
    
    locale_lines = [
        '',
        '# Set UTF-8 locale to avoid encoding issues',
        'export LANG=en_US.UTF-8',
        'export LC_ALL=en_US.UTF-8',
        ''
    ]
    lines = lines[:insert_pos] + locale_lines + lines[insert_pos:]
    text = '\n'.join(lines)

# Replacements (using regex patterns that work with encoding issues)
replacements = [
    # Title
    (r'生成生产环境配置文件', 'Generate Production Environment Configuration'),
    (r'鐢熸垚鐢熶骇鐜鍨嬮厤缃枃浠?', 'Generate Production Environment Configuration'),
    
    # User input prompts
    (r'请输入配置信息.*', 'Please enter configuration (press Enter for default values):'),
    (r'API端口', 'API Port'),
    (r'管理员用户名', 'Admin Username'),
    (r'允许的CORS来源', 'CORS Origins'),
    (r'镜像标签', 'Image Tag'),
    
    # Status messages
    (r'正在生成强随机密码', 'Generating strong random passwords'),
    (r'密码生成完成', 'Password generation completed'),
    (r'配置文件生成成功', 'Configuration file generated successfully'),
    
    # File info
    (r'文件位置', 'File location'),
    (r'文件权限', 'File permissions'),
    (r'重要信息', 'Important information'),
    (r'请妥善保存', 'Please save carefully'),
    
    # Next steps
    (r'下一步', 'Next steps'),
    (r'查看完整配置', 'View full config'),
    (r'查看凭证信息', 'View credentials'),
    (r'保存凭证后删除', 'Delete credentials after saving'),
    (r'开始部署', 'Start deployment'),
    
    # Credentials
    (r'凭证信息已保存到', 'Credentials saved to'),
]

# Apply replacements
import re
for pattern, replacement in replacements:
    text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

# Write back
with open(filepath, 'wb') as f:
    f.write(text.encode('utf-8'))

print("Converted Chinese prompts to English")
print("Please test: bash scripts/generate_production_config.sh")

