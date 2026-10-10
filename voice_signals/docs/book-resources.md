# Маппинг книжных ресурсов

Назначение: единая точка навигации между полным первоисточником (PDF) и локальной Markdown-выжимкой. Численные результаты из выжимок считаются заявленными авторами, пока не проведена независимая проверка протокола и данных.

| Теги | Полная статья | MD-выжимка | Прикладной фокус |
|---|---|---|---|
| `har`, `computer-vision`, `video`, `deep-learning`, `semi-supervised`, `handcrafted-features`, `datasets` | [030020_1_5.0301806.pdf](030020_1_5.0301806.pdf) | [030020_1_5.0301806-summary.md](books/030020_1_5.0301806-summary.md) | Архитектура HAR-конвейера, малая разметка, robustness |
| `har`, `wireless-sensing`, `wifi-csi`, `rssi`, `fmcw`, `uwb`, `edge`, `privacy`, `multimodal` | [030033_1_5.0327756.pdf](030033_1_5.0327756.pdf) | [030033_1_5.0327756-summary.md](books/030033_1_5.0327756-summary.md) | Мультимодальность, переносимость, latency и privacy |
| `emotion-recognition`, `physiological-signals`, `deap`, `fft`, `feature-fusion`, `xgboost`, `spectral-features`, `subject-independent` | [050028_1_5.0328667.pdf](050028_1_5.0328667.pdf) | [050028_1_5.0328667-summary.md](books/050028_1_5.0328667-summary.md) | Спектральные признаки, fusion, табличные baselines |
| `speech-signal`, `hurst-exponent`, `rescaled-range`, `r-s-analysis`, `nonlinear-dynamics`, `aphasia`, `dysarthria`, `speech-pathology`, `permutation-test`, `characteristic-time` | [crm358.pdf](kuzenkov/crm358.pdf) | [crm358.md](kuzenkov/crm358.md) | Modified R/S-анализ, Hurst `H`, характерное время `T`, статистическое сравнение речевых патологий |

## Правила маппинга

- Путь в колонке «Полная статья» ведёт к PDF, который хранится в `voice_signals/docs/`.
- Путь в колонке «MD-выжимка» ведёт к файлу с кратким содержанием, критической оценкой и рекомендациями для проекта.
- Новые ресурсы добавляются одной строкой; теги должны быть короткими и пригодными для поиска.
- Для чисел и параметров в выжимке указывать страницу PDF и явно отмечать, если это только результат авторов без независимой репликации.
