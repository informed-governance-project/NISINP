#! /usr/bin/env bash

#
# Update the software.
#

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

COMMITID="${1:-master}"

set -e
#set -x

git fetch origin --tags
git checkout "$COMMITID"
npm ci
poetry install --only main
poetry run python manage.py collectstatic --no-input
poetry run python manage.py migrate
poetry run python manage.py compilemessages

echo -e "✨ 🌟 ✨"
echo -e "${GREEN}Update finished. You can now restart the service.${NC} Example:"
echo "    sudo systemctl restart apache2.service"

exit 0
