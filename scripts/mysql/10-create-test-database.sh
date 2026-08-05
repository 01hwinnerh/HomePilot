#!/bin/sh
set -eu

test_database="${MYSQL_TEST_DATABASE:-homepilot_test}"
business_database="${MYSQL_DATABASE:-homepilot}"
application_user="${MYSQL_USER:-homepilot}"

case "$test_database" in
  ""|*[!A-Za-z0-9_]*)
    echo "MYSQL_TEST_DATABASE may contain only letters, digits, and underscores." >&2
    exit 1
    ;;
esac

test_database_lower="$(printf '%s' "$test_database" | tr '[:upper:]' '[:lower:]')"
business_database_lower="$(printf '%s' "$business_database" | tr '[:upper:]' '[:lower:]')"

if [ "$test_database_lower" = "$business_database_lower" ]; then
  echo "MYSQL_TEST_DATABASE must differ from MYSQL_DATABASE." >&2
  exit 1
fi

case "$test_database_lower" in
  *test*) ;;
  *)
    echo "MYSQL_TEST_DATABASE must contain 'test'." >&2
    exit 1
    ;;
esac

case "$application_user" in
  ""|*[!A-Za-z0-9_]*)
    echo "MYSQL_USER may contain only letters, digits, and underscores." >&2
    exit 1
    ;;
esac

mysql --protocol=socket -uroot -p"${MYSQL_ROOT_PASSWORD}" <<-EOSQL
CREATE DATABASE IF NOT EXISTS \`${test_database}\`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;
GRANT ALL PRIVILEGES ON \`${test_database}\`.* TO '${application_user}'@'%';
EOSQL
