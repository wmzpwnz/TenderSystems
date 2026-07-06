# План настройки КриптоПро для SOAP API ЕИС

## Текущая ситуация

- ⚠️ Токен физ. лица должен быть получен в ЛК ПМД ЕИС и храниться только в `.env` или secret manager
- ✅ SOAP клиент: готов, формирует правильные запросы
- ❌ КриптоПро + Stunnel: не установлены
- ❌ TLS с ГОСТ: требуется для подключения к ЕИС

## Почему нужен КриптоПро?

Сервер ЕИС (`int.zakupki.gov.ru`) использует TLS с российскими алгоритмами шифрования ГОСТ.
Стандартный curl/Python не поддерживают ГОСТ. Нужен специальный proxy (Stunnel с КриптоПро).

## Схема подключения

```
[Python Backend] → HTTP → [localhost:8080] → [Stunnel+ГОСТ] → HTTPS/ГОСТ → [int.zakupki.gov.ru:443]
```

---

## Вариант 1: Docker-контейнер (РЕКОМЕНДУЕТСЯ)

### Шаг 1: Создать Dockerfile

```dockerfile
FROM redos/redos:7.3

# Установка КриптоПро CSP 5.0
RUN yum install -y wget && \
    wget -O /tmp/csp.tar.gz "https://cryptopro.ru/sites/default/files/private/csp/50/12000/linux-amd64.tgz" && \
    tar -xzf /tmp/csp.tar.gz -C /tmp && \
    cd /tmp/linux-amd64 && \
    ./install.sh && \
    rm -rf /tmp/*

# Копируем конфиг stunnel
COPY stunnel.conf /etc/opt/cprocsp/stunnel/stunnel.conf

# Порт для приема соединений
EXPOSE 8080

# Запуск stunnel
CMD ["/opt/cprocsp/sbin/amd64/stunnel_thread"]
```

### Шаг 2: Конфиг stunnel.conf

```ini
; Клиентский режим
client = yes

; Логирование  
output = /var/log/stunnel.log
pid = /var/run/stunnel.pid

; Сервис для ЕИС
[eis-ip]
accept = 0.0.0.0:8080
connect = int.zakupki.gov.ru:443

; Без проверки сертификата сервера (для тестов)
verify = 0
```

### Шаг 3: Запуск

```bash
docker build -t cryptopro-stunnel .
docker run -d -p 8080:8080 --name eis-proxy cryptopro-stunnel
```

### Шаг 4: Тест

```bash
curl -X POST http://localhost:8080/eis-integration/services/getDocsIP \
  -H "Content-Type: text/xml" \
  -d '<soap request>'
```

---

## Вариант 2: Linux VPS

### Требования
- RedOS 7.3 / CentOS 7+ / Ubuntu 20.04+
- Минимум 1GB RAM, 10GB диск

### Шаг 1: Скачать КриптоПро CSP 5.0

```bash
# Скачиваем с официального сайта (нужна регистрация)
wget "https://cryptopro.ru/sites/default/files/private/csp/50/12000/linux-amd64_deb.tgz"
tar -xzf linux-amd64_deb.tgz
cd linux-amd64_deb
sudo ./install.sh
```

### Шаг 2: Настройка Stunnel

```bash
# Создаем конфиг
sudo nano /etc/opt/cprocsp/stunnel/stunnel.conf
```

Содержимое:
```ini
client = yes
output = /var/log/stunnel.log
pid = /var/run/stunnel.pid

[eis-ip]
accept = 0.0.0.0:8080
connect = int.zakupki.gov.ru:443
verify = 0
```

### Шаг 3: Запуск Stunnel

```bash
sudo /opt/cprocsp/sbin/amd64/stunnel_thread
```

### Шаг 4: Проверка

```bash
curl http://localhost:8080/eis-integration/services/getDocsIP?wsdl
```

---

## Вариант 3: Windows VPS

### Шаг 1: Скачать и установить

1. КриптоПро CSP 5.0: https://cryptopro.ru/products/csp/downloads
2. Stunnel-msspi: https://cryptopro.ru/sites/default/files/private/csp/50/12000/stunnel_msspi.exe

### Шаг 2: Настройка stunnel.conf

```ini
output = C:\Stunnel\stunnel.log
client = yes

[https]
accept = localhost:8080
connect = int.zakupki.gov.ru:443
verify = 0
```

### Шаг 3: Запуск

```
C:\Stunnel\stunnel_msspi.exe
```

---

## Обновление Backend

После настройки Stunnel, нужно обновить SOAP клиент:

```python
# backend/app/services/eis_soap_client.py

# Было:
self.base_url = "https://int.zakupki.gov.ru/eis-integration/services/getDocsIP"

# Стало:
self.base_url = "http://localhost:8080/eis-integration/services/getDocsIP"  # Через Stunnel
```

---

## Альтернатива: Без КриптоПро (текущее решение)

Пока SOAP API недоступен, система работает через **HTML-парсинг**:

- ✅ Работает без КриптоПро
- ✅ Поддерживает все фильтры
- ✅ Актуальные данные с zakupki.gov.ru
- ⚠️ Медленнее чем SOAP API
- ⚠️ Зависит от структуры HTML (может сломаться при изменении дизайна)

---

## Оценка времени

| Задача | Время |
|--------|-------|
| Аренда VPS с Linux | 10 мин |
| Установка КриптоПро | 30 мин |
| Настройка Stunnel | 15 мин |
| Обновление backend | 10 мин |
| Тестирование | 30 мин |
| **Итого** | **~1.5 часа** |

---

## Стоимость

- **VPS (минимальный)**: от $5/месяц (DigitalOcean, Hetzner)
- **КриптоПро CSP**: бесплатная trial версия или ~3000 руб/год для организации
- **Docker**: бесплатно

---

## Рекомендация

**Для быстрого старта**: используйте текущее решение с HTML-парсингом (работает сейчас).

**Для production**: настройте Docker-контейнер с КриптоПро на отдельном VPS.



