# csvpeek

A tiny, zero-dependency CSV profiler. Point it at a CSV file and it tells you what is
actually inside: the inferred type of every column, how many values are missing, how many
distinct values there are, and the range or distribution.

No pandas, no numpy, no install step — just the Python standard library.

```console
$ python -m csvpeek examples/orders.csv
COLUMN      TYPE   NULLS      UNIQUE  MIN         MAX         MEAN
----------  -----  ---------  ------  ----------  ----------  -----
order_id    int    0/8 (0%)   8       1001        1008        1004
customer    text   0/8 (0%)   5       -           -           -
country     text   0/8 (0%)   3       -           -           -
amount      float  1/8 (12%)  7       15.75       210         84.11
currency    text   0/8 (0%)   3       -           -           -
paid        bool   0/8 (0%)   2       False       True        0.625
created_at  date   0/8 (0%)   7       2024-01-05  2024-01-14  -
```

## Why

Most "profile my dataframe" tools drag in a 40 MB dependency tree. When all you need is a
quick sanity check before a migration, an import or a schema change, `csvpeek` gets out of
the way: one file in, one table out, and `--json` if you want to pipe it somewhere.

## Install

Requires Python 3.9+.

```bash
git clone https://github.com/guoshi2026/csvpeek.git
cd csvpeek
python -m csvpeek examples/orders.csv
```

Or install it as a command:

```bash
pip install .
csvpeek examples/orders.csv
```

## Usage

```
csvpeek <path> [--json] [--top N] [--encoding ENC]
```

| Flag | Default | Meaning |
| --- | --- | --- |
| `--json` | off | Emit a JSON report instead of the text table |
| `--top N` | `5` | Keep the `N` most frequent values per column |
| `--encoding` | `utf-8-sig` | Input encoding; `utf-8-sig` also eats a BOM |

Exit codes: `0` success, `1` empty or header-less file, `2` file not found.

### JSON output

```console
$ python -m csvpeek examples/orders.csv --json
{
  "columns": [
    {
      "name": "amount",
      "type": "float",
      "rows": 8,
      "nulls": 1,
      "null_ratio": 0.125,
      "unique": 7,
      "min": 15.75,
      "max": 210.0,
      "mean": 84.107143,
      "top": []
    }
  ],
  "column_count": 7,
  "row_count": 8
}
```

### Library use

```python
from csvpeek import profile_csv, to_json

profiles = profile_csv("examples/orders.csv")
print(to_json(profiles)["columns"][3]["mean"])  # 84.107143
```

## What it detects

| Type | Rule |
| --- | --- |
| `int` | Every non-empty value parses as an integer |
| `float` | Every non-empty value parses as a float |
| `bool` | Values are in `true/false/yes/no/y/n/1/0` **and** at least one word form appears |
| `date` | Every value matches `%Y-%m-%d`, `%Y/%m/%d`, `%d/%m/%Y` or `%Y-%m-%dT%H:%M:%S` |
| `text` | Anything else |
| `empty` | The column has no values at all |

Notes on the numbers:

- `NULLS` counts empty strings; whitespace-only cells count as empty.
- `MEAN` on a `bool` column is the ratio of true values.
- In the table, `MEAN` is trimmed to 4 significant digits (`1004` for an average of `1004.5`);
  `--json` carries full precision.
- The delimiter is sniffed from the first 8 KB, falling back to `,`; `;`, tab and `|` work too.

## Limits

This is a profiling tool, not a data engine. It streams row by row but keeps every distinct
value in memory to compute cardinality and top-k, so a 10 GB file will not be happy. Keep
it to files that fit in RAM, or sample first.

## Development

```bash
python -m unittest discover -s tests -v
```

11 tests, no third-party test runner.

## License

MIT — see [LICENSE](LICENSE).
