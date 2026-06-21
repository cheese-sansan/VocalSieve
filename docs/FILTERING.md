# Filtering and rejection reasons

VocalSieve applies acoustic rules before transcription rules. The first failed
rule becomes the file's `reject_code`; `reject_detail` contains the measured
value or backend error. Changing thresholds affects future jobs and resumed
files whose cache key changes.

| Code | Meaning | Configuration | Adjustment guidance |
| --- | --- | --- | --- |
| `duration_too_short` | Audio is shorter than the minimum duration. | `min_duration` | Lower only when very short utterances are useful. |
| `energy_too_low` | Average RMS energy is too low. | `min_rms` | Lower after listening for quiet but usable speech. |
| `spectral_centroid_too_low` | The signal has little high-frequency content. | `min_centroid` | Lower for dark voices or narrow-band recordings. |
| `no_speech` | The backend assigned a high no-speech probability. | `no_speech_threshold` | Raise only after reviewing false rejects. |
| `text_too_short` | Transcript character count is below the minimum. | `min_text_length` | Lower for one-character utterances. |
| `text_too_long` | Transcript character count exceeds the maximum. | `max_text_length` | Raise when longer utterances are acceptable. |
| `repeated_characters` | Transcript contains a suspicious repeated run. | `repeat_char_threshold` | Raise if legitimate repetitions are common. |
| `hallucination_keyword` | Transcript contains a known hallucination phrase. | none | Review both audio and transcript. |
| `physics_error` | Audio decoding or acoustic analysis failed. | none | Check integrity, codec support, and FFmpeg. |
| `transcription_error` | The transcription backend failed. | none | Run `vocalsieve doctor` and inspect events. |

`selected` means the file passed every rule and ranked within `top_n`.
`transcription_passed` means it passed every rule but ranked outside `top_n`;
it was not rejected. `physics_rejected` and `transcription_rejected` are rule
rejections, while `error` represents a processing failure.

Every export keeps the row-oriented `vocalsieve-report.csv` and
`vocalsieve-report.json` formats and adds `vocalsieve-summary.json`. Run
`vocalsieve report JOB_ID` for the same aggregate explanation without
re-exporting audio, or add `--json` for machine-readable output.
