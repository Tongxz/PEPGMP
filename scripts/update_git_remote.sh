#!/bin/bash
# 更新 Git 远程仓库 URL
# 用于将远程仓库名称从 Pyt 更新为 PEPGMP

set -e

OLD_REPO_NAME="Pyt"
NEW_REPO_NAME="PEPGMP"
GITHUB_USER="Tongxz"
INTERNAL_SERVER="192.168.30.83"

echo "🔄 更新 Git 远程仓库 URL..."
echo ""

# 检查是否在 Git 仓库中
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "❌ 错误: 当前目录不是 Git 仓库"
    exit 1
fi

# 显示当前配置
echo "📋 当前远程仓库配置:"
git remote -v
echo ""

# 更新 origin (GitHub)
if git remote get-url origin &>/dev/null; then
    OLD_URL=$(git remote get-url origin)

    # 检测 URL 格式并生成新 URL
    if echo "$OLD_URL" | grep -q "github.com"; then
        # GitHub HTTPS URL
        NEW_URL="https://github.com/${GITHUB_USER}/${NEW_REPO_NAME}.git"
    elif echo "$OLD_URL" | grep -q "git@github.com"; then
        # GitHub SSH URL
        NEW_URL="git@github.com:${GITHUB_USER}/${NEW_REPO_NAME}.git"
    else
        # 使用替换方式
        NEW_URL=$(echo "$OLD_URL" | sed "s|/${OLD_REPO_NAME}\.git|/${NEW_REPO_NAME}.git|g" | sed "s|/${OLD_REPO_NAME}$|/${NEW_REPO_NAME}.git|g")
    fi

    if [ "$OLD_URL" != "$NEW_URL" ]; then
        echo "  🔄 修改 origin:"
        echo "     旧: $OLD_URL"
        echo "     新: $NEW_URL"
        git remote set-url origin "$NEW_URL"
        echo "  ✅ origin 已更新"
    else
        echo "  ℹ️  origin 已是最新配置: $OLD_URL"
    fi
fi

echo ""

# 更新 internal
if git remote get-url internal &>/dev/null; then
    OLD_URL=$(git remote get-url internal)

    # 检测 URL 格式并生成新 URL
    if echo "$OLD_URL" | grep -q "$INTERNAL_SERVER"; then
        # 内部服务器 URL
        NEW_URL="git@${INTERNAL_SERVER}:${NEW_REPO_NAME}.git"
    else
        # 使用替换方式
        NEW_URL=$(echo "$OLD_URL" | sed "s|:${OLD_REPO_NAME}\.git|:${NEW_REPO_NAME}.git|g" | sed "s|:${OLD_REPO_NAME}$|:${NEW_REPO_NAME}.git|g")
    fi

    if [ "$OLD_URL" != "$NEW_URL" ]; then
        echo "  🔄 修改 internal:"
        echo "     旧: $OLD_URL"
        echo "     新: $NEW_URL"
        git remote set-url internal "$NEW_URL"
        echo "  ✅ internal 已更新"
    else
        echo "  ℹ️  internal 已是最新配置: $OLD_URL"
    fi
fi

echo ""

# 显示更新后的配置
echo "✅ 更新后的远程仓库配置:"
git remote -v
echo ""

# 测试连接（可选，需要用户确认）
echo "🔍 是否测试远程连接？(y/n)"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo ""
    echo "测试 origin 连接..."
    if git fetch origin --dry-run 2>&1 | head -5; then
        echo "  ✅ origin 连接正常"
    else
        echo "  ⚠️  origin 连接失败，请检查:"
        echo "     - 仓库是否已在平台上重命名"
        echo "     - URL 是否正确"
        echo "     - 认证信息是否正确"
    fi

    if git remote get-url internal &>/dev/null; then
        echo ""
        echo "测试 internal 连接..."
        if git fetch internal --dry-run 2>&1 | head -5; then
            echo "  ✅ internal 连接正常"
        else
            echo "  ⚠️  internal 连接失败，请检查:"
            echo "     - 服务器地址是否正确"
            echo "     - SSH 密钥是否配置"
        fi
    fi
fi

echo ""
echo "🎉 更新完成！"
echo ""
echo "💡 提示:"
echo "  - 如果仓库在 GitHub/GitLab 上尚未重命名，请先在平台上重命名"
echo "  - 如果连接测试失败，请检查仓库名称和认证信息"
echo "  - 团队其他成员也需要执行相同操作更新远程 URL"
