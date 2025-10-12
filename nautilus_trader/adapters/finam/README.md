---
  # Создай все необходимые директории одной командой
  mkdir -p common/schemas http parsing

  Пояснение структуры:
  - common/ - общие компоненты (константы, enums, credentials, schemas)
  - common/schemas/ - Pydantic модели для валидации JSON ответов API
  - http/ - HTTP клиент для REST API (аналог Binance)
  - parsing/ - парсеры для конвертации Finam моделей → Nautilus моделей
---
