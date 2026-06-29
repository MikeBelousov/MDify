# Conservative Latin Rescue и BGR-контракт OCR

## Целевое поведение

В режиме `auto` каждая строка сначала распознаётся Eslavic PP-OCRv5. Latin
PP-OCRv5 запускается только для пустого либо явно плохого результата без
кириллицы и может заменить Eslavic только после строгой проверки. Явные режимы
`cyrillic` и `latin` не меняются. PP-OCRv6 не участвует в runtime и не входит в
релизные сборки; его adapter остаётся в исходниках только как изолированный и
протестированный компонент.

## Изменения кода

### Маршрутизация Auto

В `workers/ocr/text_quality.py` должны оставаться отдельные rescue-пороги:

```python
LATIN_TRIGGER_CONFIDENCE = 0.50
LATIN_ACCEPT_CONFIDENCE = 0.90
EMPTY_ESLAV_ACCEPT_CONFIDENCE = 0.85
LATIN_MIN_QUALITY_GAIN = 0.20
LATIN_MIN_SIMILARITY = 0.70
LATIN_MIN_SOURCE_LENGTH = 5
```

Они намеренно не меняют общие `AUTO_CONFIDENCE_THRESHOLD` и
`MIN_ACCEPTABLE_QUALITY`.

В `workers/ocr/auto_router.py` Latin вызывается для пустого Eslavic либо при
confidence ниже trigger/структурной ошибке (`replacement-or-control`,
`repetition`). Непустой исходный текст должен содержать Latin-букву и не должен
содержать кириллицу; цифры и пунктуация сами по себе не являются trigger.

Для непустого Eslavic замена принимается только если Latin-текст непустой,
Latin-only, без structural errors, имеет confidence не ниже `0.90`, улучшает
quality минимум на `0.20`, исходный нормализованный текст имеет не меньше пяти
символов, а нормализованное Levenshtein-сходство не ниже `0.70`. Нормализация:
Unicode NFKC, `casefold()` и схлопывание пробелов. Для пустого Eslavic сходство
не проверяется; confidence и quality Latin должны быть не ниже `0.85`.

`latin_retry_count` считает попытки, `latin_accept_count` — принятые замены.
`ppocrv6_retry_count` сохраняется в результате только для wire-совместимости и
всегда равен нулю.

### Runtime и модели

- `workers/ocr/rapidocr_engine.py` создаёт для Auto Eslavic и ленивый Latin,
  но не PP-OCRv6.
- `workers/ocr/model_registry.py` и `workers/ocr/line_recognition.py` не имеют
  production factory для PP-OCRv6.
- `workers/ocr/model_manifest.json` содержит только detector, classifier,
  Eslavic, Latin и font.
- PP-OCRv6 ONNX и dictionary удалены из `workers/ocr/models` и `.gitattributes`.
- `workers/build/download_models.py`, macOS verifier и Windows workflow требуют
  точного совпадения файлов с manifest, поэтому старый файл из CI cache также
  блокирует релиз.

### BGR/RGB

`workers/ocr/ppocrv6_adapter.py` использует явный контракт: `PIL.Image`
принимается как RGB и один раз переводится в BGR; NumPy crop от RapidOCR уже
считается BGR и не переставляется повторно. Unit-тест подаёт один физический
цвет одновременно как PIL RGB и NumPy BGR и требует одинаковый tensor.

## Что проверить перед деплоем

1. Unit/integration tests проходят без загрузки PP-OCRv6 и подтверждают все
   trigger/acceptance/rejection сценарии, порядок строк и explicit modes.
2. `download_models.py --verify-only` проходит, а в каталоге моделей и готовых
   macOS/Windows artifacts нет ни одного unlisted-файла или `PP-OCRv6`.
3. Безопасный benchmark сначала создаёт cache по одной странице в процессе;
   score не загружает модели и сравнивает thresholds `0.40/0.45/0.50` с одним
   и тем же Eslavic-only baseline.
4. После каждого этапа должно быть `harmed=0`, NED не ниже baseline, CER не
   выше baseline и ни одного RSS/timeout нарушения. Canary, Stress,
   Balanced-20 и Full запускаются отдельными командами; Full требует ручного
   подтверждения.
5. Финальный threshold — максимальный прошедший из трёх. Если на полном наборе
   нет безопасного threshold с хотя бы одной улучшенной страницей и одной
   принятой заменой, Latin Rescue отключается и Auto выпускается Eslavic-only.

Основные риски перед релизом: confidence разных recognizer может быть плохо
калиброван, similarity может отвергать полезные длинные исправления, пустой
Eslavic — более рискованный путь без similarity, а устаревший build cache может
вернуть удалённую модель. Поэтому качество оценивается по сохранённым кандидатам
и по группам EN/RU × digital/photo, а release artifact проверяется отдельно.

## Команды benchmark

Каждый этап запускается отдельной командой. Для повторных этапов используется
один cache и `--resume`; scorer выбирает только файлы указанного stage.

```bash
python script/benchmark_conservative_latin.py cache \
  --stage canary \
  --dataset-dir .benchmarks/MDPBench-Mini-RU-EN \
  --ground-truth-dir .benchmarks/results/mdpbench-mini-full/ground_truth \
  --models-dir workers/ocr/models \
  --cache-dir .benchmarks/results/conservative-latin-cache \
  --resume

python script/benchmark_conservative_latin.py score \
  --stage canary \
  --cache-dir .benchmarks/results/conservative-latin-cache \
  --output .benchmarks/results/conservative-latin-canary.json
```

Для `stress` и `balanced20` меняются только `--stage` и имя output. Для
`full` обеим командам передаётся `--dataset-dir`; этот этап не запускается до
ручного подтверждения результатов предыдущих этапов.
