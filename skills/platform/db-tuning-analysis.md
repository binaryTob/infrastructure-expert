---
id: "db_tuning_analysis"
name: "Database Tuning Analysis"
version: "1.0"
category: "database"
phase: "optimize"
risk: "readonly"
execution_mode: "auto"
depends_on: ["database_analysis"]
triggers: ["PRESENT:postgresql_socket", "PRESENT:mysql_socket", "PRESENT:psql", "PRESENT:mysql"]
provides: ["pg_settings", "pg_buffers", "pg_connections", "pg_wal", "my_cnf", "innodb_buffer", "my_connections", "slow_queries", "index_usage", "vacuum_status"]
parameters:
  OUTPUT_DIR: { type: "filepath", default: "{{RUN_DIR}}/db-tuning" }
  SSH_TARGET: { type: "string", required: true }
output: { format: "json", schema: "output_schema" }
---

# Database Tuning Analysis

## Objective
Deep-dive into PostgreSQL and MySQL/MariaDB configuration and runtime metrics to identify
tuning opportunities: buffer sizes, connection limits, WAL/redo log, slow queries,
missing indexes, vacuum/analyze, and replication lag. Complements `database_analysis`
(which does discovery + basic config) with optimization-focused checks.

## Commands

### PostgreSQL detailed settings + runtime (if psql available)
```bash
# [risk:ro] [mode:auto] [requires:psql]
ssh {{SSH_TARGET}} 'echo "=== PG SETTINGS ==="; sudo -u postgres psql -c "SELECT name, setting, unit, short_desc FROM pg_settings WHERE name IN ('"'"'shared_buffers'"'"', '"'"'effective_cache_size'"'"', '"'"'work_mem'"'"', '"'"'maintenance_work_mem'"'"', '"'"'max_connections'"'"', '"'"'max_wal_size'"'"', '"'"'checkpoint_timeout'"'"', '"'"'wal_buffers'"'"', '"'"'default_statistics_target'"'"', '"'"'random_page_cost'"'"', '"'"'effective_io_concurrency'"'"', '"'"'autovacuum'"'"', '"'"'autovacuum_max_workers'"'"', '"'"'log_min_duration_statement'"'"') ORDER BY name;" 2>/dev/null || psql -c "SELECT name, setting, unit FROM pg_settings WHERE name IN ('"'"'shared_buffers'"'"', '"'"'effective_cache_size'"'"', '"'"'work_mem'"'"', '"'"'maintenance_work_mem'"'"', '"'"'max_connections'"'"', '"'"'max_wal_size'"'"', '"'"'checkpoint_timeout'"'"') ORDER BY name;" 2>/dev/null; echo; echo "=== CONNECTIONS ==="; sudo -u postgres psql -c "SELECT count(*) as total, count(*) FILTER (WHERE state = '"'"'active'"'"') as active, count(*) FILTER (WHERE state = '"'"'idle'"'"') as idle, count(*) FILTER (WHERE state = '"'"'idle in transaction'"'"') as idle_in_tx FROM pg_stat_activity;" 2>/dev/null; echo; echo "=== REPLICATION ==="; sudo -u postgres psql -c "SELECT * FROM pg_stat_replication;" 2>/dev/null || echo "no replication"'
```

### PostgreSQL cache hit ratio + vacuum status
```bash
# [risk:ro] [mode:auto] [requires:psql]
ssh {{SSH_TARGET}} 'sudo -u postgres psql -c "SELECT '"'"'heap'"'"' as type, sum(heap_blks_hit) / nullif(sum(heap_blks_hit) + sum(heap_blks_read),0) as hit_ratio FROM pg_statio_user_tables UNION ALL SELECT '"'"'index'"'"', sum(idx_blks_hit) / nullif(sum(idx_blks_hit) + sum(idx_blks_read),0) FROM pg_statio_user_tables;" 2>/dev/null; echo; echo "=== VACUUM ==="; sudo -u postgres psql -c "SELECT relname, last_vacuum, last_autovacuum, last_analyze, last_autoanalyze, n_dead_tup FROM pg_stat_user_tables WHERE n_dead_tup > 1000 ORDER BY n_dead_tup DESC LIMIT 10;" 2>/dev/null'
```

### PostgreSQL slow queries (if pg_stat_statements)
```bash
# [risk:ro] [mode:auto] [requires:psql]
ssh {{SSH_TARGET}} 'sudo -u postgres psql -c "SELECT query, calls, total_exec_time, mean_exec_time, rows FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;" 2>/dev/null || echo "pg_stat_statements not enabled"'
```

### PostgreSQL missing indexes (sequential scans)
```bash
# [risk:ro] [mode:auto] [requires:psql]
ssh {{SSH_TARGET}} 'sudo -u postgres psql -c "SELECT relname, seq_scan, seq_tup_read, idx_scan FROM pg_stat_user_tables WHERE seq_scan > 100 AND seq_tup_read / nullif(seq_scan,0) > 1000 ORDER BY seq_tup_read DESC LIMIT 10;" 2>/dev/null'
```

### MySQL/MariaDB config + status (if mysql available)
```bash
# [risk:ro] [mode:auto] [requires:mysql]
ssh {{SSH_TARGET}} 'echo "=== MYSQL VARIABLES ==="; mysql -e "SHOW GLOBAL VARIABLES WHERE Variable_name IN ('"'"'innodb_buffer_pool_size'"'"', '"'"'innodb_log_file_size'"'"', '"'"'innodb_log_files_in_group'"'"', '"'"'innodb_flush_log_at_trx_commit'"'"', '"'"'max_connections'"'"', '"'"'thread_cache_size'"'"', '"'"'query_cache_type'"'"', '"'"'query_cache_size'"'"', '"'"'slow_query_log'"'"', '"'"'long_query_time'"'"', '"'"'innodb_flush_method'"'"', '"'"'sync_binlog'"'"');" 2>/dev/null; echo; echo "=== STATUS ==="; mysql -e "SHOW GLOBAL STATUS WHERE Variable_name IN ('"'"'Threads_connected'"'"', '"'"'Threads_running'"'"', '"'"'Aborted_connects'"'"', '"'"'Innodb_buffer_pool_read_requests'"'"', '"'"'Innodb_buffer_pool_reads'"'"', '"'"'Created_tmp_disk_tables'"'"', '"'"'Created_tmp_tables'"'"', '"'"'Select_full_join'"'"', '"'"'Slow_queries'"'"');" 2>/dev/null'
```

### MySQL slow queries + buffer pool hit ratio
```bash
# [risk:ro] [mode:auto] [requires:mysql]
ssh {{SSH_TARGET}} 'mysql -e "SELECT (1 - (Variable_value / nullif((select Variable_value from performance_schema.global_status where Variable_name='"'"'Innodb_buffer_pool_read_requests'"'"'),0))) as buffer_pool_miss_rate FROM performance_schema.global_status WHERE Variable_name='"'"'Innodb_buffer_pool_reads'"'"';" 2>/dev/null || mysql -e "SHOW GLOBAL STATUS LIKE '"'"'Innodb_buffer_pool_read%'"'"';" 2>/dev/null; echo; echo "=== SLOW QUERIES ==="; mysql -e "SELECT COUNT(*) as slow_count, SUM(Query_time) as total_time FROM mysql.slow_log WHERE start_time > DATE_SUB(NOW(), INTERVAL 1 HOUR);" 2>/dev/null || echo "slow_log table not available"'
```

### MySQL index usage + missing indexes (schema heuristic)
```bash
# [risk:ro] [mode:auto] [requires:mysql]
ssh {{SSH_TARGET}} 'mysql -e "SELECT TABLE_SCHEMA, TABLE_NAME, INDEX_NAME, CARDINALITY FROM information_schema.STATISTICS WHERE NON_UNIQUE=1 AND CARDINALITY < 10 ORDER BY CARDINALITY LIMIT 20;" 2>/dev/null; echo "=== FULL TABLE SCANS ==="; mysql -e "SELECT TABLE_SCHEMA, TABLE_NAME, SUM(ROWS_EXAMINED) as rows_examined, COUNT(*) as queries FROM performance_schema.events_statements_summary_by_digest WHERE DIGEST_TEXT NOT LIKE '"'"'%EXPLAIN%'"'"' AND ROWS_EXAMINED > 10000 GROUP BY TABLE_SCHEMA, TABLE_NAME ORDER BY rows_examined DESC LIMIT 10;" 2>/dev/null || echo "performance_schema not enabled"'
```

## Analysis

### PostgreSQL
- **`shared_buffers` < 25% RAM** (on dedicated DB): inefficient I/O; aim for 25-40%.
- **`work_mem` too high** * `max_connections` = OOM risk under concurrency.
- **`effective_cache_size` not set**: planner assumes low cache, picks bad plans.
- **`checkpoint_timeout` > 15min** or `max_wal_size` too small: checkpoint spikes.
- **Hit ratio < 99%** (heap or index): increase `shared_buffers` / `effective_cache_size`.
- **`autovacuum = off`**: dead tuples accumulate, bloat, wraparound risk.
- **Tables with `n_dead_tup` > 100k**: autovacuum not keeping up; tune `autovacuum_vacuum_scale_factor`.
- **`pg_stat_statements` missing**: no query-level visibility; enable it.
- **High `seq_scan` + high `seq_tup_read/seq_scan`**: missing index candidate.
- **Replication lag > 1s**: follower falling behind; check WAL sender / network.

### MySQL/MariaDB
- **`innodb_buffer_pool_size` < 70% RAM** (dedicated): aim for 70-80%.
- **`innodb_log_file_size` too small** (< 256M): frequent checkpoint flushes.
- **`innodb_flush_log_at_trx_commit` = 0 or 2**: durability risk (data loss on crash).
- **`slow_query_log = OFF`**: no visibility into slow queries.
- **Buffer pool hit ratio < 99%**: increase buffer pool or investigate cold queries.
- **`Created_tmp_disk_tables` / `Created_tmp_tables` > 10%**: queries need better indexes or `tmp_table_size` increase.
- **`Select_full_join` > 0**: missing indexes on join columns.
- **`innodb_flush_method` != `O_DIRECT`**: double buffering with OS cache.
- **`max_connections` high + low `thread_cache_size`**: connection churn overhead.
- **Replication `Seconds_Behind_Master` > 5s**: follower lag.

## False Positives
- Dev/staging DBs with tiny buffers are expected; weight by environment.
- `pg_stat_statements` / `performance_schema` may be disabled by policy; flag as INFO not WARNING.
- A single slow query in `pg_stat_statements` isn't a problem unless it's frequent.

## Evidence
- `pg-settings.txt`, `pg-connections.txt`, `pg-cache.txt`, `pg-vacuum.txt`, `pg-slow.txt`, `pg-seqscan.txt`, `my-variables.txt`, `my-status.txt`, `my-buffer.txt`, `my-slow.txt`, `my-index.txt`

## Security
Read-only. No `ALTER SYSTEM`, `SET GLOBAL`, `ANALYZE`, `VACUUM`, or `CREATE INDEX` (Level 3).