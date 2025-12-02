#!/bin/bash

################################################################################
# Check Database Container Health
# Purpose: Diagnose database container health check failures
################################################################################

set -e

echo "========================================================================="
echo "Database Container Health Check"
echo "========================================================================="
echo ""

# Check if container exists
if ! docker ps -a | grep -q pepgmp-postgres-prod; then
    echo "[ERROR] Container pepgmp-postgres-prod not found"
    exit 1
fi

echo "1. Container Status:"
docker ps -a | grep pepgmp-postgres-prod
echo ""

echo "2. Container Health Status:"
HEALTH_STATUS=$(docker inspect pepgmp-postgres-prod --format='{{.State.Health.Status}}' 2>/dev/null || echo "no healthcheck")
echo "  Health Status: $HEALTH_STATUS"
echo ""

if [ "$HEALTH_STATUS" != "no healthcheck" ]; then
    echo "3. Health Check Details:"
    docker inspect pepgmp-postgres-prod --format='{{json .State.Health}}' | python3 -m json.tool 2>/dev/null || echo "  (Unable to parse health status)"
    echo ""
fi

echo "4. Recent Logs (last 30 lines):"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker logs pepgmp-postgres-prod --tail 30 2>&1 | tail -30
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "5. Environment Variables:"
docker inspect pepgmp-postgres-prod --format='{{range .Config.Env}}{{println .}}{{end}}' | grep -E 'POSTGRES|DATABASE' || echo "  (No database-related env vars found)"
echo ""

echo "6. Test Database Connection:"
echo "  Attempting to connect to database..."
if docker exec pepgmp-postgres-prod pg_isready -U pepgmp_prod 2>/dev/null; then
    echo "  [OK] Database is ready"
else
    echo "  [ERROR] Database is not ready"
    echo ""
    echo "  Trying to connect with psql..."
    docker exec pepgmp-postgres-prod psql -U pepgmp_prod -d pepgmp_production -c "SELECT 1;" 2>&1 || echo "  [ERROR] Connection failed"
fi
echo ""

echo "========================================================================="
echo "Recommendations"
echo "========================================================================="
echo ""

if [ "$HEALTH_STATUS" = "unhealthy" ]; then
    echo "[ACTION REQUIRED] Container is unhealthy"
    echo ""
    echo "Try the following:"
    echo "  1. Check logs for errors: docker logs pepgmp-postgres-prod"
    echo "  2. Restart database: docker-compose -f docker-compose.prod.yml restart database"
    echo "  3. If persistent, reset database:"
    echo "     docker-compose -f docker-compose.prod.yml down -v database"
    echo "     docker-compose -f docker-compose.prod.yml up -d database"
    echo "     sleep 60"
    echo "     docker-compose -f docker-compose.prod.yml up -d"
elif [ "$HEALTH_STATUS" = "starting" ]; then
    echo "[INFO] Container is still starting, please wait..."
    echo "  Health check may take 30-60 seconds"
elif [ "$HEALTH_STATUS" = "healthy" ]; then
    echo "[OK] Container is healthy"
else
    echo "[INFO] Health check status: $HEALTH_STATUS"
fi

echo "========================================================================="

