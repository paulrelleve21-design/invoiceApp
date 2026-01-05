#!/usr/bin/env python3
"""
Helper script to migrate data from the current SQLite DB to a PostgreSQL DB.

Usage:
  python scripts/sqlite_to_postgres.py --database-url postgresql://user:pass@host:5432/dbname

What it does:
  - Runs `manage.py dumpdata` (excludes admin/contenttypes permissions)
  - Runs `manage.py migrate` against the provided Postgres DATABASE_URL
  - Runs `manage.py loaddata` to import the dumped JSON into Postgres

Notes:
  - Ensure the target Postgres server exists and the user has privileges.
  - Create a filesystem backup of `db.sqlite3` before running.
"""

import argparse
import os
import shlex
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANAGE = os.path.join(ROOT, 'manage.py')
DATA_DUMP = os.path.join(ROOT, 'scripts', 'data_dump.json')


def run(cmd, env=None):
    print('> ' + cmd)
    parts = shlex.split(cmd)
    res = subprocess.run(parts, env=env)
    if res.returncode != 0:
        print('Command failed:', cmd)
        sys.exit(res.returncode)


def main():
    parser = argparse.ArgumentParser(description='Migrate SQLite -> PostgreSQL (Django)')
    parser.add_argument('--database-url', required=True, help='Target Postgres DATABASE_URL')
    parser.add_argument('--dump-file', default=DATA_DUMP, help='Path to store dump JSON')
    args = parser.parse_args()

    # 1) Dump data from current settings (uses current env)
    print('\nStep 1: Dumping data from current database (SQLite)')
    cmd = f'python "{MANAGE}" dumpdata --natural-foreign --natural-primary --exclude auth.permission --exclude contenttypes --exclude admin.logentry -o "{args.dump_file}"'
    run(cmd)

    # 2) Set DATABASE_URL for subsequent commands
    print('\nStep 2: Applying migrations on target Postgres DB')
    env = os.environ.copy()
    env['DATABASE_URL'] = args.database_url

    # Ensure dj-database-url will pick it up via settings
    run(f'python "{MANAGE}" migrate', env=env)

    # 3) Load data into Postgres
    print('\nStep 3: Loading dumped data into Postgres')
    run(f'python "{MANAGE}" loaddata "{args.dump_file}"', env=env)

    print('\nMigration complete. Verify data in pgAdmin or via Django admin.')


if __name__ == '__main__':
    main()
