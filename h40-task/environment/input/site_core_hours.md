# Site core hours — Ardleigh Trust pathology

Match the register `site` column to a row below. Times are 24-hour local trust time.

| Site code | Site name | Core open | Core close |
|---|---|---|---|
| MAIN | Ardleigh Main laboratory | 08:00 | 18:00 |
| RIVERSIDE | Riverside Clinic laboratory | 08:00 | 17:00 |

Notes:

- Core close is exclusive of the closing instant for starting a new tier-2 clock: a release at
  exactly the close time starts on the next open morning.
- Weekends use the same open/close times as weekdays unless the date is listed in
  `bank_holidays.csv`.
- If `site` is blank, treat the row as `MAIN`.

- Dated amendments may supersede Riverside hours for some release dates; see `procedure_amendment_2026-07-01.md`.
