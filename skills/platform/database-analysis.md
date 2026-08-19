---
id: "database_analysis"
name: "Database Analysis"
version: "1.0"
category: "database"
phase: "analyze"
risk: "readonly"
execution_mode: "auto"
depends_on: ["network_analysis"]
triggers: ["PRESENT:postgresql_socket", "PRESENT:mysql_socket", "PRESENT:redis_socket"]
provides: ["db_engine", "db_connections", "db_size", "db_settings"]
parameters:
  OUTPUT_DIR: { type: "filepath", default: "{{RUN_DIR}}/database" }
  SSH_TARGET: { type: "string", required: true }
output: { format: "json", schema: "output_schema" }
---
# Database Analysis

## Objective
Detect what database engines are running, their size, connections, and key configuration parameters.

## Commands

### Detect database processes and ports
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'for p in postgres psql mysql mariadb mysqld redis-server redis-cli mongod mongosh; do echo -n "$p: "; command -v $p 2>/dev/null || echo "absent"; done; echo; ss -tlnp 2>/dev/null | grep -E ":5432|:3306|:6379|:27017|:9042|:9200"'
```

### Remote / external database config (apps pointing at a DB off-host)
```bash
# [risk:ro] [mode:auto]
ssh {{SSH_TARGET}} 'echo "=== DB CONFIG FILES ==="; find /opt /home /root /srv /app -maxdepth 5 -type f \( -name "database.yml" -o -name "database.yaml" -o -name "my.cnf" -o -name ".env" -o -name ".env.production" -o -name "settings.py" \) 2>/dev/null | head -30; echo; echo "=== CONNECTION TARGETS ==="; grep -rhoiE "(host|hostname|DB_HOST)[\"'"'"' :=\t]+[A-Za-z0-9.\-]+|DATABASE_URL=[a-z]+://[^@ \n]+@[^ \n]+" /opt /home /root /srv 2>/dev/null | grep -viE "localhost|127\.0\.0\.1" | sort -u | head -30'
```

### Remote DB reachability (non-destructive connect probe)
```bash
# [risk:probe] [mode:auto]
ssh {{SSH_TARGET}} 'for hp in $(grep -rhoiE "(host|hostname)[\"'"'"' :=\t]+[A-Za-z0-9.\-]+" /opt /home /root /srv 2>/dev/null | grep -oiE "[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$" | grep -viE "localhost|\.com\.ar$" | sort -u | head -10); do port=$(grep -rhoiE "port[\"'"'"' :=\t]+[0-9]+" /opt /home /root /srv 2>/dev/null | grep -oE "[0-9]{2,5}" | head -1); p=${port:-5432}; timeout 4 bash -c "</dev/tcp/$hp/$p" 2>/dev/null && echo "REACHABLE $hp:$p" || echo "UNREACHABLE $hp:$p"; done'
```

### PostgreSQL (if psql available)
```bash
# [risk:ro] [mode:auto] [requires:psql]
ssh {{SSH_TARGET}} 'echo "=== VERSION ==="; psql --version 2>/dev/null; echo; echo "=== DATABASES ==="; sudo -u postgres psql -c "\l" 2>/dev/null || psql -c "\l" 2>/dev/null; echo; echo "=== CONNECTIONS ==="; sudo -u postgres psql -c "SELECT count(*) as total_connections FROM pg_stat_activity;" 2>/dev/null || true; echo; echo "=== SETTINGS ==="; sudo -u postgres psql -c "SELECT name,setting FROM pg_settings WHERE name IN ('max_connections','shared_buffers','effective_cache_size','work_mem','maintenance_work_mem','wal_buffers','max_wal_size','checkpoint_timeout')" 2>/dev/null || true'
```

### MySQL/MariaDB (if mysql available)
```bash
# [risk:ro] [mode:auto] [requires:mysql]
ssh {{SSH_TARGET}} 'echo "=== VERSION ==="; mysql --version 2>/dev/null; echo; echo "=== DATABASES ==="; mysql -e "SHOW DATABASES;" 2>/dev/null; echo; echo "=== STATUS ==="; mysql -e "SHOW GLOBAL STATUS LIKE '"'"'%conn%'"'"';" 2>/dev/null; echo; echo "=== VARIABLES ==="; mysql -e "SHOW GLOBAL VARIABLES LIKE '"'"'innodb_buffer_pool%'"'"';" 2>/dev/null'
```

### Redis (if redis-cli available)
```bash
# [risk:ro] [mode:auto] [requires:redis-cli]
ssh {{SSH_TARGET}} 'echo "=== INFO ==="; redis-cli INFO server 2>/dev/null; echo; echo "=== MEMORY ==="; redis-cli INFO memory 2>/dev/null; echo; echo "=== STATS ==="; redis-cli INFO stats 2>/dev/null; echo; echo "=== CLIENTS ==="; redis-cli INFO clients 2>/dev/null'
```

## Analysis
- `shared_buffers` too low (< 25% RAM on dedicated server): inefficient I/O.
- `max_connections` > 500 without connection pooling: risk.
- Redis without `requirepass` on 0.0.0.0: CRITICAL exposure.
- Slow queries log enabled: good. Not enabled: WATCH.

## Security
Read-only. Never run write queries. Flag exposed databases without authentication.
