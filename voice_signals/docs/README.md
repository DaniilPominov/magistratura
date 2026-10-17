# Документация проекта voice_signals

Навигация по документам проекта.

---

## 📊 Текущее состояние

**[Оценка состояния проекта (17.10.2026)](project-status-2026-10-17.md)** ⭐  
Полный анализ Iteration 02: что реализовано, критические блокеры, план третьей итерации, вопросы к научному руководителю.

**[Вопросы к научному руководителю](questions-for-advisor.md)** 🔴  
Критические вопросы (доступ к данным, разметка, этика) и методические (приоритет признаков, метрики).

---

## 📝 Отчёты по итерациям

- **[Отчёт Iteration 01](report-iteration-01.md)** – MVP Energy VAD, методическая основа
- **[Отчёт Iteration 02](report-iteration-02.md)** – Синтетический корпус, аудит, feature extractor, piecewise fit для T
- **[Краткая сводка Iteration 02](ITERATION-02-SUMMARY.md)** – краткая версия отчёта

---

## 📚 Руководства

**[Руководство по использованию](usage-guide.md)**  
Установка, API, примеры кода, структура проекта, конфигурация, FAQ.

**[Контракты данных](contracts.md)**  
Спецификация `SegmentRecord`, `FileAuditRecord`, `FrameFeatureRecord`, `ExperimentRecord`.

**[Рабочий журнал VAD Iteration 01](vad-iteration-01.md)**  
Черновик первой итерации (технические заметки).

---

## 🔬 Литературная база

### Основная методика

**[Кузенков, Логинов (2014) – выжимка](kuzenkov/crm358.md)**  
Modified R/S-анализ речевых патологий. Основа для показателя Хёрста H и характерного времени T.  
📄 Полный PDF: [kuzenkov/crm358.pdf](kuzenkov/crm358.pdf)

### Дополнительная литература

**[Обзор: Нейроинформатика 2021](literature-review-neuroinformatics-2021.md)**  
YOLOv4 + DeepSORT, упругие карты, спайковые нейронные сети, нейросетевое декодирование.  
📄 Полный PDF: [Нейроинформатика, ее приложения и анализ данных-2021.pdf](Нейроинформатика,%20ее%20приложения%20и%20анализ%20данных-2021.pdf)

**[Маппинг книжных ресурсов](book-resources.md)**  
Единая таблица: теги → полный PDF → MD-выжимка → прикладной фокус.

**Выжимки:**
- [HAR на видео (AIP 2025)](books/030020_1_5.0301806-summary.md) – конвейер, semi-supervised, robustness
- [Wireless HAR (AIP 2026)](books/030033_1_5.0327756-summary.md) – мультимодальность, privacy, deployment
- [Emotion recognition (DEAP)](books/050028_1_5.0328667-summary.md) – спектральные признаки, XGBoost/RF

---

## 🎯 Планирование

**[План задач](../agent/tasks/README.md)**  
Критический путь, волны для нескольких исполнителей, MVP-gate, правила работы.

**Задачи:**
- [TASK-00: Bootstrap](../agent/tasks/TASK-00-project-bootstrap.md) ✅
- [TASK-01: Аудит WAV](../agent/tasks/TASK-01-wav-audit.md) ✅ базовая, ⏳ полная
- [TASK-02: Feature extractor](../agent/tasks/TASK-02-feature-extractor.md) ✅ базовая
- [TASK-03: Hurst/DFA](../agent/tasks/TASK-03-hurst-dfa.md) ⏳
- [TASK-04: Entropy](../agent/tasks/TASK-04-entropy.md) ⏳
- [TASK-05: RQA/Lyapunov](../agent/tasks/TASK-05-rqa-lyapunov.md) ⏳
- [TASK-06: VAD adapters](../agent/tasks/TASK-06-vad-adapters.md) ✅ интерфейс, ⏳ WebRTC
- [TASK-07: Pseudo-labels](../agent/tasks/TASK-07-pseudo-labels.md) ⏳
- [TASK-08: Label Studio](../agent/tasks/TASK-08-label-studio.md) 🔴 блокер
- [TASK-09: Синтетический корпус](../agent/tasks/TASK-09-synthetic-corpus.md) ✅ минимальная
- [TASK-10: MVP-gate](../agent/tasks/TASK-10-mvp-evaluation.md) ⏳
- [TASK-11: Собственный VAD](../agent/tasks/TASK-11-custom-vad.md) ✅ partial (piecewise fit), 🔴 полная

**Правила:**
- [Глобальные правила проекта](../agent/rules/project-agreements.md)

---

## 🔴 Критические блокеры

1. **Нет реального корпуса** → запросить у научного руководителя
2. **Нет gold-разметки** → TASK-08, IAA ≥ 0.8
3. **Нет WebRTC baseline** → TASK-06 полная
4. **Нет subject-level split** → реализовать алгоритм

**Действие:** Связаться с научным руководителем, см. [questions-for-advisor.md](questions-for-advisor.md)

---

## 📂 Дополнительные материалы

**PDF-документы в директории `docs/`:**
- `030020_1_5.0301806.pdf` – HAR на видео
- `030033_1_5.0327756.pdf` – Wireless HAR
- `050028_1_5.0328667.pdf` – Emotion recognition (DEAP)
- `sjim394.pdf` – дополнительный источник
- `Диагностика свойств интеллекта по временным характеристикам речи человека.pdf` – текущая попытка извлечения (повреждён)
- `Нейроинформатика, ее приложения и анализ данных-2021.pdf` – обработан ✅

**TXT-выгрузки (черновики):**
- `Диагностика свойств интеллекта по временным характеристикам речи человека.txt`
- `Нейроинформатика, ее приложения и анализ данных-2021.txt`

---

## 🏗️ Структура документации

```
docs/
├── README.md                          # Этот файл
├── project-status-2026-10-17.md       # ⭐ Оценка состояния
├── questions-for-advisor.md           # 🔴 Вопросы к научруку
├── report-iteration-01.md             # Отчёт Iteration 01
├── report-iteration-02.md             # Отчёт Iteration 02
├── usage-guide.md                     # Руководство пользователя
├── contracts.md                       # Контракты данных
├── book-resources.md                  # Маппинг литературы
├── literature-review-neuroinformatics-2021.md  # Обзор
├── kuzenkov/
│   ├── crm358.md                      # Выжимка методики
│   └── crm358.pdf                     # Полный PDF
└── books/
    ├── 030020_1_5.0301806-summary.md  # HAR видео
    ├── 030033_1_5.0327756-summary.md  # Wireless HAR
    └── 050028_1_5.0328667-summary.md  # Emotion DEAP
```

---

**Последнее обновление:** 17 октября 2026  
**Версия проекта:** 0.2.0  
**Статус:** Iteration 02 завершена, готовы к Iteration 03
