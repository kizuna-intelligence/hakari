# hakari とは

git 履歴と行数だけから修正率とホットスポットを出すツールです。
言語には依存しません。
外部サービスに何も送信しません。

## 導入

必要なもの: Python 3.10 以上、git 2.31 以上。

```console
pipx install git+https://github.com/kizuna-intelligence/hakari
cd <リポジトリ>
hakari init
hakari measure
```

GitHub のソースからインストールします。

出力先は `docs/quality-metrics/metrics.json` と
`docs/quality-metrics/report.md` です。

## 設定項目

`hakari.toml` の `[hakari]` に設定します。同じ内容は
`pyproject.toml` の `[tool.hakari]` でも書けます。

| キー | 既定値 | 意味 |
|---|---|---|
| `branch` | `"auto"` | `origin/HEAD` → `main` → `master` → 現在のブランチの順で履歴を読む |
| `timezone` | `"Asia/Tokyo"` | 著者日時を日付へ丸めるタイムゾーン |
| `recent_days` | `30` | 修正率の窓の日数 |
| `hotspot_days` | `90` | ホットスポットの窓の日数 |
| `fix.fix_types` | `["fix", "hotfix"]` | 修正型とみなす型 |
| `fix.feat_types` | `["feat"]` | 機能型とみなす型 |
| `fix.subject_pattern` | `"\\b(fix\|hotfix\|revert\|regression\|bug)\\b"` | 型が取れない件名を修正型と判定する正規表現 |
| `hotspot.min_lines` | `800` | ホットスポットの行数の下限(この値より大きい) |
| `hotspot.min_rework` | `1000` | 書換量(`rework = churn - created_lines`)の下限 |
| `paths.exclude` | `[...]` | ベンダー、ロック、生成物、ビルド出力など計測から除外するパターン。既定値は `**/node_modules/**`, `**/_vendor/**`, `**/vendor/**`, `**/*.lock`, `**/package-lock.json`, `**/dist/**`, `**/build/**`, `**/target/**`, `**/.next/**`, `**/*.min.js`, `**/*.pb.go`, `**/*.xcodeproj/**`, `**/*.xcassets/**` |
| `paths.tests` | `[...]` | テストファイルのパターン。既定値は `**/tests/**`, `**/test/**`, `**/*_test.go`, `**/test_*.py`, `**/*_test.py`, `**/*.test.ts`, `**/*.test.tsx`, `**/*.spec.ts`, `**/*Tests.swift`, `**/*_test.rs` |
| `paths.docs` | `["docs/**", "**/*.md"]` | 文書ファイルのパターン |
| `paths.production_extensions` | `["go", "py", "rs", "swift", "ts", "tsx", "js", "kt", "java", "c", "cc", "cpp", "h"]` | 本番ファイルとして扱う拡張子 |
| `paths.version_files` | `["**/pyproject.toml", "**/package.json", "**/__init__.py", "release-manifest.json", "**/Cargo.toml"]` | 横断の判定から除外する版数ファイルのパターン |
| `components` | `{}` | コンポーネント名からパスパターン配列への対応。省略時は第1階層ディレクトリ |
| `output.dir` | `"docs/quality-metrics"` | `metrics.json` と `report.md` の出力ディレクトリ |

`hotspot.min_commits` を設定している場合は起動時に `ConfigError: unknown config key: hotspot.min_commits` で停止します。移行として `hotspot.min_rework` を新たに設定してください。

## 指標の定義

### fixes — 修正率

| 値 | 定義 |
|---|---|
| 着地の型 | 件名の先頭 `type(scope)!:` の type。併合コミット(`Merge pull request #N from org/branch`)は本文の PR 件名、なければブランチ名の先頭(`fix/...`、`hotfix/...`、`feat/...`)。型が取れなければ件名を `subject_pattern`(既定 `\b(fix\|hotfix\|revert\|regression\|bug)\b`、大文字小文字無視)で判定し、一致すれば `fix`、しなければ `unknown` |
| 窓 | 既定30日(`recent_days`)。著者日付を `timezone` で日付に丸め、`--as-of`(既定: 今日)を終端とする閉区間。前の30日も同時に計算して前期比を出す |
| `landings` | 窓内の着地数(本番ファイルを触ったもの) |
| `fix_share` | 型が `fix_types`(既定 `fix`, `hotfix`)の着地数 / `landings` |
| `fix_to_feat` | `fix_types` の着地数 / `feat_types`(既定 `feat`)の着地数。`feat` が0なら `null` |
| `hotfix_count` | 型が `hotfix`、または件名に `hotfix` を含む着地数 |
| `revert_count` | 件名が `Revert "` で始まる、または型 `revert` の着地数 |
| `by_type` | 型ごとの着地数(`fix`, `hotfix`, `feat`, `refactor`, `test`, `chore`, `docs`, `revert`, `other`, `unknown`) |
| `unknown_share` | `unknown` の割合。高い(> 0.3)場合、件名規約がなく型比は信頼できないと report に明記する |

### hotspots — ホットスポット

| 値 | 対象 | 定義 |
|---|---|---|
| `lines` | HEAD の本番ファイル | HEAD でのファイルの行数(改行数。バイナリは対象外) |
| `commits` | HEAD の本番ファイル | `hotspot_days`(既定90日)の窓でそのファイルを触った着地数(リネームは `--follow` せず、現在のパスで数える。リネーム直後のファイルは過小評価になる旨を報告)。参考値。判定には使わない |
| `churn` | HEAD の本番ファイル | 同じ窓での追加+削除行 |
| `created_lines` | HEAD の本番ファイル | `hotspot_days` の窓で新規作成着地されたファイルの追加行 |
| `rework` | HEAD の本番ファイル | `churn - created_lines` |
| ホットスポット | HEAD の本番ファイル | `lines > min_lines` かつ `rework >= min_rework` |
| `count` | ホットスポット | ホットスポットの数。全体とコンポーネント別 |
| `files` | ホットスポット | ホットスポット一覧(`path`, `component`, `lines`, `commits`, `churn`, `created_lines`, `rework`)を `rework` 降順。加えて「惜しい」候補（`near`）を別一覧 |
| `files_over_min_lines` | 本番ファイル | 補助値。全体とコンポーネント別 |
| `max_file_lines` | 本番ファイル | 補助値。全体とコンポーネント別 |

「惜しい」候補は `lines > min_lines` かつ `min_rework / 2 <= rework < min_rework`。

既知の限界として、**リネーム追跡なし**のため、リネーム直後のファイルは `commits` や
`churn`、`rework` が過小評価になります。

窓の前からあるファイルは窓内の作成着地を引けないため、`rework` は `churn` と同じです。
それ自体は窓内の変更しか数えないため、判定には影響しません。

## モノレポでの数え方

- コンポーネント = パスのパターン集合。設定で与え、なければ第1階層のディレクトリ名を自動採用する(直下のファイルは `(root)`)。
- 1つの着地が複数コンポーネントに帰属する(各側に数える)。
- 横断着地は各側に数えたうえで別に計上する。`(触)` と `(専)` の2通りを出す。
- リポジトリ全体の合計は着地単位で1回だけ数えるので、コンポーネント別の和にはならない。
- 版数ファイルを除くと横断でなくなる着地は、横断として数えない。リリース時の版数更新による見かけ上の横断を、コンポーネント境界の横断として数えないためである。

## 開発・テスト

```console
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
python -m pytest -q
```

通常のテストは一時ディレクトリに作成した合成リポジトリを使います。
3,000コミットの性能テストも含まれます。既存リポジトリを使った読み取り専用の
検証を行う場合は、対象を明示してください。

```console
HAKARI_TEST_REPO=/path/to/repository python -m pytest -q tests/test_real_repos.py
```
