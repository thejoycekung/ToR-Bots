#bin/sh

# Install for citext
apt-get update && apt-get install -y postgresql-contrib

echo "SELECT 'CREATE DATABASE torstats' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'torstats')\gexec" | psql -U postgres

# Run commmands

psql -U postgres setup.sql

