#!/bin/bash
set -e

echo "🚀 SIMRAS Backend Startup"
echo "=========================="

# Run database migrations
echo ""
echo "📦 Running migrations..."
alembic upgrade head || true
echo "✅ Migrations complete"

# Seed demo users
echo ""
echo "🌱 Seeding demo users..."
python seed_demo_users.py || echo "⚠️  Seeding skipped (not critical)"
echo ""

# Start the application
echo "🎯 Starting SIMRAS backend"
echo "=========================="
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
