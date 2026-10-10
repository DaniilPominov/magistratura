# TASK-08. Label Studio и конвертеры разметки

Роль: Annotation workflow agent. Файл результата: `labelstudio_import_export.py`.

## Цель
Получить gold-разметку для собственного VAD, а затем расширить ее до
четырехклассовой разметки речевых событий. Без этого нельзя честно обучить и
оценить собственный VAD.

## Вход
- WAV или локальный доступ к аудио.
- Pseudo-labels TASK-07, если они уже доступны.
- На первом этапе: `speech` / `non_speech`.
- На расширенном этапе: `speech`, `silent_pause`, `hesitation`, `artifact`.

## Выход
1. Локальный проект Label Studio.
2. Конфиг разметки.
3. Импорт задач.
4. Экспорт аннотаций.
5. Конвертер в SegmentRecord.
6. Отчёт о прогрессе.

## Требования
- Приватность: локальный запуск или controlled environment; сырое аудио не уходит во внешние сервисы.
- Два разметчика на пилоте 1–2 часа с одинаковыми файлами; inter-annotator
  agreement. Для собственного VAD сначала считать бинарное согласие
  `speech/non_speech`.
- Статусы: draft, reviewed, accepted, rejected, needs_discussion.
- Заметки разметчика: сомнительная гезитация, слышно дыхание, возможный артефакт, перекрытие.

## Шаги
1. Конфиг Label Studio (Audio + Labels). Для первой итерации использовать
   бинарные классы `speech` и `non_speech`; четыре класса включить после
   первого результата собственного VAD. Проверить актуальный синтаксис.
```xml
<View>
  <Audio name="audio" value="$audio"/>
  <Labels name="label" toName="audio">
    <Label value="speech"/>
    <Label value="non_speech"/>
  </Labels>
</View>
```
2. Импорт аудио: локальные пути, URL внутри controlled storage, батчи.
3. Импорт pseudo-labels как черновиков: is_pseudo_label=true, review_status=draft, визуально отличимы от ручной разметки.
4. Экспорт: Label Studio JSON -> SegmentRecord CSV/Parquet. Проверить единицы времени, соответствие файла, start/end, отсутствие потерь меток.
5. Round-trip: аннотация -> экспорт -> импорт -> сравнение, допуск 1 мс.
6. Отчёт: files_total, files_labeled, hours_labeled, segments_by_label, avg_segment_duration, review_status_distribution, annotator_agreement_pilot.

## Критерии приёмки
1. Для первой итерации разметчик выставляет `speech` или `non_speech`.
2. Расширенная конфигурация поддерживает четыре класса MVP.
3. Pseudo-labels импортируются как черновики и никогда не считаются gold.
4. Таймкоды в секундах.
5. Конвертер не теряет данные.
6. Аннотации разделяются по разметчикам.
7. Считается overlap между аннотациями.
8. Работает локально без обязательной внешней передачи аудио.

## Тесты
- Pseudo-label CSV -> Label Studio JSON.
- Бинарная gold-разметка -> `SegmentRecord` для TASK-11.
- Label Studio JSON -> internal CSV.
- Round-trip с допуском 1 мс.
- Согласованность двух аннотаций: frame-level agreement, segment IoU, duration difference, Cohen's kappa или Krippendorff's alpha.
- Приватность: конфиг по умолчанию не отправляет аудио наружу.

## Ошибки, которых избегать
- Миллисекунды в одном месте и секунды в другом.
- Потеря subject_id при экспорте.
- Смешение pseudo-labels и gold без флага.
- Не сохранённая версия конфига Label Studio.
- Пересечения сегментов без модели overlap.

## Инструкция агенту
Настрой локальный workflow Label Studio: сначала для бинарной gold-разметки
`speech` / `non_speech`, затем для четырёх классов. Поддержи импорт аудио,
импорт pseudo-labels как черновиков, экспорт и конвертер в SegmentRecord.
Добавь round-trip тест и расчёт agreement для пилотных двойных разметок.
Сырое аудио во внешние сервисы по умолчанию не отправлять.
