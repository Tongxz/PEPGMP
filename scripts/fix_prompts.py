#!/usr/bin/env python3
# Fix prompts in generate_production_config.sh

filepath = 'scripts/generate_production_config.sh'

with open(filepath, 'rb') as f:
    content = f.read()

text = content.decode('utf-8', errors='ignore')

# Fix user input section
old_prompts = [
    ('# 鑾峰彇鐢ㄦ埛杈撳叆', '# Get user input'),
    ('echo "璇疯緭鍏ラ厤缃俊鎭', 'echo "Please enter configuration (press Enter for default values):'),
    ('read -p "API绔彛', 'read -p "API Port'),
    ('read -p "绠＄悊鍛樼敤鎴峰悕', 'read -p "Admin Username'),
    ('read -p "鍏佽CORS鏉ユ簮', 'read -p "CORS Origins'),
    ('read -p "闀滃儚鏍囩', 'read -p "Image Tag'),
    ('echo "姝ｅ湪鐢熸垚寮洪殢鏈哄瘑鐮', 'echo "Generating strong random passwords...'),
    ('echo "鉁?瀵嗙爜鐢熸垚瀹屾垚"', 'echo "✓ Password generation completed"'),
]

for old, new in old_prompts:
    text = text.replace(old, new)

# Fix title
text = text.replace('echo -e "${BLUE}鐢熸垚鐢熶骇鐜鍨嬮厤缃枃浠?{NC}"', 'echo -e "${BLUE}Generate Production Environment Configuration${NC}"')

# Fix success message
text = text.replace('echo -e "${GREEN}閰嶇疆鏂囦欢鐢熸垚鎴愬姛锛?{NC}"', 'echo -e "${GREEN}Configuration file generated successfully!${NC}"')

# Fix next steps
text = text.replace('echo "鍑瘉淇℃伅宸蹭繚瀛樺埌:', 'echo "Credentials saved to:')
text = text.replace('echo "涓嬩竴姝?', 'echo "Next steps:')
text = text.replace('echo "  1. 鏌ョ湅瀹屾暣閰嶇疆:', 'echo "  1. View full config:')
text = text.replace('echo "  2. 鏌ョ湅鍑瘉淇℃伅:', 'echo "  2. View credentials:')
text = text.replace('echo "  3. 淇濆瓨鍑瘉鍚庡垹闄?', 'echo "  3. Delete credentials after saving:')
text = text.replace('echo "  4. 寮€濮嬮儴缃?', 'echo "  4. Start deployment:')

with open(filepath, 'wb') as f:
    f.write(text.encode('utf-8'))

print("Fixed prompts to English")

