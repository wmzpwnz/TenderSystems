#!/bin/bash
# Скрипт для тестирования системы после запуска

echo "=========================================="
echo "Тестирование системы 'Тендерный Хакер'"
echo "=========================================="
echo ""

# Цвета для вывода
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Проверка статуса контейнеров
echo "1. Проверка статуса контейнеров..."
docker-compose ps

echo ""
echo "2. Проверка подключения к БД..."
docker-compose exec -T postgres psql -U tenderuser -d tenderdb -c "SELECT version();" 2>/dev/null && echo -e "${GREEN}✓ БД работает${NC}" || echo -e "${RED}✗ БД не доступна${NC}"

echo ""
echo "3. Проверка API backend..."
sleep 2
curl -s http://localhost:8000/health | jq . 2>/dev/null && echo -e "${GREEN}✓ Backend API работает${NC}" || echo -e "${RED}✗ Backend API не отвечает${NC}"

echo ""
echo "4. Проверка количества тендеров в БД..."
TENDER_COUNT=$(docker-compose exec -T postgres psql -U tenderuser -d tenderdb -t -c "SELECT COUNT(*) FROM tenders;" 2>/dev/null | tr -d ' ')
echo "Тендеров в БД: $TENDER_COUNT"

if [ "$TENDER_COUNT" -eq "0" ]; then
    echo -e "${YELLOW}⚠ БД пуста. Запускаем синхронизацию...${NC}"
    echo ""
    echo "5. Запуск синхронизации тендеров..."
    curl -X POST "http://localhost:8000/api/v1/tenders/sync?page=1&page_size=10" \
         -H "Content-Type: application/json" 2>/dev/null | jq . || echo "Ошибка синхронизации"
    
    echo ""
    echo "6. Проверка после синхронизации..."
    sleep 3
    NEW_COUNT=$(docker-compose exec -T postgres psql -U tenderuser -d tenderdb -t -c "SELECT COUNT(*) FROM tenders;" 2>/dev/null | tr -d ' ')
    echo "Тендеров в БД после синхронизации: $NEW_COUNT"
    
    if [ "$NEW_COUNT" -gt "0" ]; then
        echo -e "${GREEN}✓ Синхронизация успешна!${NC}"
        echo ""
        echo "Примеры тендеров:"
        docker-compose exec -T postgres psql -U tenderuser -d tenderdb -c "SELECT id, eis_id, LEFT(title, 50) as title FROM tenders LIMIT 3;" 2>/dev/null
    else
        echo -e "${RED}✗ Синхронизация не добавила тендеры${NC}"
    fi
else
    echo -e "${GREEN}✓ В БД уже есть тендеры${NC}"
    echo ""
    echo "Примеры тендеров:"
    docker-compose exec -T postgres psql -U tenderuser -d tenderdb -c "SELECT id, eis_id, LEFT(title, 50) as title FROM tenders LIMIT 3;" 2>/dev/null
fi

echo ""
echo "=========================================="
echo "Тестирование завершено"
echo "=========================================="
echo ""
echo "Доступ к системе:"
echo "  - Frontend: http://localhost:3000"
echo "  - Backend API: http://localhost:8000"
echo "  - API Docs: http://localhost:8000/docs"














