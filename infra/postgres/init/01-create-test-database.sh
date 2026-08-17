#!/bin/sh
# Создаёт отдельную базу для интеграционных тестов.
#
# Тех. ТЗ 7 запрещает гонять интеграционные тесты на общей dev-базе, поэтому
# рядом с рабочей базой поднимается `<POSTGRES_DB>_test`.
#
# Скрипт выполняется только при первой инициализации кластера, то есть когда
# том postgres-data пустой. После `docker compose down -v` — выполнится снова.
set -eu

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-SQL
	CREATE DATABASE "${POSTGRES_DB}_test" OWNER "$POSTGRES_USER";
SQL

echo "создана база для тестов: ${POSTGRES_DB}_test"
