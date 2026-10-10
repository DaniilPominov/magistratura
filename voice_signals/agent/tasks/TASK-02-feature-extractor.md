# TASK-02. Извлечение кадровых признаков

Роль: Speech feature agent. Файл результата: `feature_extractor.py`.

## Цель
Воспроизводимый feature extractor, общий для статистической ветви, нейронной ветви, fusion-слоя и pseudo-label генератора. Все модули должны использовать одну схему фрейминга.

## Вход
- Аудиосигнал или путь к WAV.
- Конфиг фрейминга и признаков.

## Выход
```text
features/{file_id}.parquet
```
или
```text
features/{file_id}/frames.npy
features/{file_id}/metadata.json
```
Метаданные: file_id, sample_rate, window_ms, hop_ms, n_frames, feature_names, feature_versions, checksum_audio, checksum_config.

Форма: `[T, F]`.

## Признаки MVP (приоритет)
1. log-Mel, 64 фильтра.
2. MFCC 20 + delta + delta-delta.
3. Short-time energy, log energy.
4. Zero-crossing rate.
5. Spectral flatness.
6. A posteriori SNR, noise floor estimate.
7. Voicing probability (простой прокси, без сложного pitch tracker).

Дополнительно, если успеется: spectral centroid, spectral entropy, a priori SNR, harmonic-to-noise proxy, LPC residual energy, subband ratios, spectral tilt.

## Шаги
1. Унификация: mono, target sample rate (например 16 kHz), float32. Исходный уровень сохранять в метаданных, чтобы нормализация не стирала информацию о паузах и артефактах.
2. Фрейминг: window_ms=25, hop_ms=10, Hann.
3. log-Mel: torchaudio (предпочтительно) или librosa. n_mels=64, n_fft 512 или 400, hop 160 и win 400 при 16 kHz; для других sample rate пересчитывать.
4. MFCC с дельтами.
5. Energy = sum(frame^2), log_energy = log(energy + eps), zcr = 0.5 * count(sign changes) / frame_length.
6. Spectral flatness = geometric_mean / arithmetic_mean power spectrum.
7. SNR и voicing через оценку шумового пола по минимумам энергии.
8. Версионирование каждого признака: например `logmel_64_v1`, `mfcc_20_delta_v1`, `snr_aposteriori_v1`, `voicing_proxy_v1`.

## Критерии приёмки
1. Детерминированный выход для файла и конфига.
2. Форма `[T, F]`.
3. Нет NaN и Inf без явного флага.
4. Все признаки имеют имя, версию, параметры.
5. Работает на 8, 16 и 48 kHz; корректность параметров проверяется тестами.
6. Сохранение и загрузка без потери связи с таймкодами.

## Тесты
- Синус: стабильный спектральный пик.
- Белый шум: высокая spectral flatness.
- Тишина: низкая энергия, предсказуемый SNR-флаг.
- Клик: высокий ZCR и транзиентный флаг.
- Низкий гудок: высокая voicing proxy.
- 1 секунда при hop 10 ms дает около 100 кадров.
- Таймкоды монотонны.
- Смена sample rate корректно меняет n_fft и hop_length.
- Regression: эталонный вектор признаков для небольшого синтетического файла.

## Ошибки, которых избегать
- Разный hop в разных модулях.
- Потеря связи кадр-время.
- Нормализация, стирающая абсолютную энергию.
- Не сохранённая версия конфига.
- Смешивание frame-level и segment-level признаков.

## Инструкция агенту
Реализуй модуль извлечения кадровых признаков. Единая схема фрейминга. Поддержи log-Mel, MFCC с дельтами, энергию, ZCR, spectral flatness, SNR и voicing proxy. Все признаки версионируй. Выход согласован по таймкодам с VAD-сегментами. Тесты на синусе, шуме, тишине, клике и гудке. Частоту дискретизации не фиксируй без конфига.
