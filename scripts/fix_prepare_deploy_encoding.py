#!/usr/bin/env python3
# Fix encoding issues in prepare_minimal_deploy.sh

filepath = 'scripts/prepare_minimal_deploy.sh'

with open(filepath, 'rb') as f:
    content = f.read()

text = content.decode('utf-8', errors='ignore')

# Fix all remaining Chinese characters with encoding issues
replacements = [
    # Status messages
    (r'鉁\?宸叉洿鏂\?', '✓ Updated:'),
    (r'鈼\?璺宠繃:', '○ Skipped:'),
    (r'鈩癸笍\s+淇℃伅:', 'ℹ️  Info:'),
    (r'鉂\?閿欒:', '❌ Error:'),
    (r'鈿狅笍\s+', '⚠️  '),
    
    # File descriptions
    (r'\(鏂囦欢宸插瓨鍦ㄤ笖鐩稿悓\)', '(file exists and identical)'),
    (r'\(鏂囦欢鏁伴噺涓嶅悓:', '(file count differs:'),
    (r'\(鏂囦欢鏁伴噺鐩稿悓:', '(file count same:'),
    (r'vs \$dst_count\)', 'vs $dst_count)'),
    (r'\$src_count\)', '$src_count)'),
    
    # Directory messages
    (r'婧愮洰褰曚负绌\?', 'Source directory is empty:'),
    (r'鐩綍涓嶅瓨鍦ㄦ垨涓虹┖锛屽皢鍒涘缓绌虹洰褰\?', 'directory does not exist or is empty, will create empty directory'),
    
    # Configuration messages
    (r'璇疯繍琛屼互涓嬪懡浠ょ敓鎴愬畬鏁寸殑閰嶇疆鏂囦欢:', 'Please run the following command to generate complete configuration file:'),
    (r'璇ヨ剼鏈細:', 'The script will:'),
    (r'鐢熸垚瀹屾暣鐨?.env.production 鏂囦欢', 'Generate complete .env.production file'),
    (r'鑷姩鐢熸垚寮洪殢鏈哄瘑鐮\?', 'Automatically generate strong random passwords'),
    (r'鍒涘缓 .env.production.credentials 鍑瘉鏂囦欢', 'Create .env.production.credentials file'),
    (r'璁剧疆姝ｇ‘鐨勬枃浠舵潈闄\?', 'Set correct file permissions'),
    (r'鏄惁鐜板湪杩愯閰嶇疆鐢熸垚鑴氭湰\?', 'Run configuration generation script now?'),
    (r'閰嶇疆鏂囦欢宸茬敓鎴\?', 'Configuration file generated'),
    (r'閰嶇疆鐢熸垚鑴氭湰涓嶅瓨鍦\?', 'Configuration generation script does not exist'),
    (r'璇峰悗鎵嬪姩杩愯閰嶇疆鐢熸垚鑴氭湰', 'Please manually run configuration generation script later'),
    (r'宸插瓨鍦紝璺宠繃鐢熸垚', 'already exists, skipping generation'),
    
    # Summary messages
    (r'閮ㄧ讲鐩綍:', 'Deployment directory:'),
    (r'鍖呭惈鐨勬枃浠:', 'Files included:'),
    (r'宸插瓨鍦\?', '(exists)'),
    (r'闇€瑕佺敓鎴\?', '(needs generation)'),
    (r'\(閰嶇疆鏂囦欢鐩綍\)', '(configuration directory)'),
    (r'\(妯″瀷鏂囦欢鐩綍\)', '(model files directory)'),
    (r'\(鏁版嵁鐩綍\)', '(data directory)'),
    (r'\(鑴氭湰鐩綍\)', '(scripts directory)'),
    (r'涓嬩竴姝ユ搷浣:', 'Next steps:'),
    (r'杩愯閰嶇疆鐢熸垚鑴氭湰:', 'Run configuration generation script:'),
    (r'閰嶇疆鏂囦欢宸插噯澶\?', 'Configuration file ready'),
    (r'鍦?1Panel 涓垱寤\?', 'Create/update Compose project in 1Panel'),
    (r'鏇存柊 Compose 椤圭洰', 'Compose project'),
    (r'宸ヤ綔鐩綍:', 'Working directory:'),
    (r'Compose 鏂囦欢:', 'Compose file:'),
    (r'楠岃瘉鍛戒护:', 'Verification command:'),
    (r'鎻愮ず:', 'Tips:'),
    (r'濡鏋滀娇鐢ㄥ凡瀵煎叆鐨勯暅鍍\?', 'If using imported images'),
    (r'纭繚 .env.production 涓 IMAGE_TAG 璁剧疆姝ｇ‘', 'ensure IMAGE_TAG in .env.production is set correctly'),
    (r'鍑瘉淇℃伅淇濆瓨鍦\?', 'Credentials saved in'),
    (r'\(濡鏋滃凡鐢熸垚\)', '(if generated)'),
    (r'閲嶆柊杩愯姝よ剼鏈', 'Re-run this script'),
    (r'鑷姩妫€娴嬫枃浠跺樊寮傦紝鍙洿鏂版洿鍙樼殑鏂囦欢', 'automatically detects file differences and only updates changed files'),
]

import re
for pattern, replacement in replacements:
    text = re.sub(pattern, replacement, text)

# Ensure file ends with newline
if not text.endswith('\n'):
    text += '\n'

with open(filepath, 'wb') as f:
    f.write(text.encode('utf-8'))

print("Fixed encoding issues in prepare_minimal_deploy.sh")

