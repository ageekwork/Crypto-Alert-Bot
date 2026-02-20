#!/bin/bash
cd /opt/crypto-alert-bot
set -a
source .env
set +a
exec python3 src/saas_main.py >> bot.log 2>&1
