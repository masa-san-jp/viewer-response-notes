# viewer-response-notes

Privacy-safeな閲覧者反応記録と、保守的な制作要件評価の正本です。記録はappend-onlyで、Research/Productionから参照できる集計結果とopaqueな外部根拠だけを扱います。

## まず知っておくこと

- `measured` は自由記述ではなく、集計カウントと明示されたprovenanceだけを保存します。
- `external` は外部根拠の参照であり、存在しないサンプル数や成果を作りません。
- 個人名、連絡先、自由回答、心理・医療診断、raw asset、credentialは保存しません。
- `UNKNOWN`、`CONTRADICTED`、`EXTERNALLY_SUPPORTED` は受入れ合格を意味せず、blind/frame reviewと併せて扱います。

## Contracts

- `schemas/viewer-response-record.schema.json`: `viewer-response-record/v1`
- `schemas/viewer-response-assessment.schema.json`: `viewer-response-assessment/v1`
- `schemas/research-signal-export.schema.json`: `research-signal-export/v1`

record validatorはaggregate-only境界、source commit/evidence provenance、決定的deduplication、append-only uniquenessを検証します。assessmentはtwo-sided Wilson 95% intervalを使い、測定5件未満は`UNKNOWN`、lower bound `>= 0.60`は`SUPPORTED`、upper bound `< 0.60`は`CONTRADICTED`、その他は`UNKNOWN`です。測定サンプルがない場合、独立した外部根拠2件は`EXTERNALLY_SUPPORTED`になりますが、意図的に`SUPPORTED`とは区別されます。

## Local checks

```bash
python3 tools/validate.py --check
python3 -m unittest discover -s tests -v
python3 tools/export_signals.py tests/fixtures/viewer-response-records.jsonl --export-id VRSE-fixture --source-commit 0123456789abcdef0123456789abcdef01234567 --output /tmp/viewer-response-export.json
```

Exportは決定的かつatomicです。同一bytesの再実行は`ALREADY_EXPORTED`、既存ファイルとの内容差分は上書きせず`VIEWER-EXPORT-CONFLICT`になります。外部API、GitHub、Driveへ送信する処理はこのrepoから起動しません。
