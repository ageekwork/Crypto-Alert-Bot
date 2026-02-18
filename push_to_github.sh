#!/bin/bash
# Push Crypto Alert Bot to GitHub
# Run this script on the server to push to your repo

echo "🚀 Pushing Crypto Alert Bot to GitHub..."
echo ""

cd /root/.openclaw/workspace/projects/crypto_alert_bot

# Option 1: Using GitHub token (recommended)
# Replace YOUR_GITHUB_TOKEN with your actual token
echo "Option 1: Using GitHub Personal Access Token"
echo "1. Go to: https://github.com/settings/tokens"
echo "2. Click 'Generate new token (classic)'"
echo "3. Select 'repo' scope"
echo "4. Copy the token"
echo "5. Run:"
echo ""
echo "git remote set-url origin https://YOUR_TOKEN@github.com/ageekwork/Crypto-Alert-Bot.git"
echo "git push -u origin main"
echo ""

# Option 2: Using SSH (if you have SSH keys set up)
echo "Option 2: Using SSH (if configured)"
echo "git remote set-url origin git@github.com:ageekwork/Crypto-Alert-Bot.git"
echo "git push -u origin main"
echo ""

# Show current git status
echo "📊 Current Git Status:"
git status

echo ""
echo "📁 Files ready to push:"
git log --oneline -1
