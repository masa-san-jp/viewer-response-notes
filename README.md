# viewer-response-notes

Private, append-only source of truth for privacy-safe viewer response records
and conservative production-requirement assessments.

The repository stores measured responses as aggregate counts and external
evidence as opaque references. It never stores free-form answers, names,
contact details, psychological or medical diagnoses, or raw assets.

## Agentic Art全体との関係と利用方法

8リポジトリ全体の人間向け案内は、親repoの[repository map](https://github.com/masa-san-jp/agentic-art-orchestration/blob/main/docs/repository-map.md)を正本とします。このREADMEにも、役割と利用入口を次の通り表示します。

```text
self-model-notes ─┐
art-history-notes ├─ normalized research signal ─┐
marketing-trends ┘                               │
                                                 ▼
viewer-response-notes ─ feedback ─→ agentic-art-orchestration
                                                 │
                                                 ▼
                                       agentic-art-research
                                                 │ production-handoff
                                                 ▼
                                       agentic-art-production
                                                 │ canonical plan
                                                 ▼
                                       agentic-art-project
                                           公開カタログ
```

| リポジトリ | 役割 |
|---|---|
| [agentic-art-orchestration](https://github.com/masa-san-jp/agentic-art-orchestration) | 全体のcontrol plane。workspace、pin、retrieval、実行、再開、検証 |
| [self-model-notes](https://github.com/masa-san-jp/self-model-notes) | 本人の明示的・同意済みの自己モデル |
| [art-history-notes](https://github.com/masa-san-jp/art-history-notes) | 美術史上の作品、技法、関係、根拠 |
| [marketing-trends-notes](https://github.com/masa-san-jp/marketing-trends-notes) | 社会・市場の変化と鮮度付きの根拠 |
| [agentic-art-research](https://github.com/masa-san-jp/agentic-art-research) | 入力知識を使った調査、仮説、要件、判断 |
| [agentic-art-production](https://github.com/masa-san-jp/agentic-art-production) | handoffを受けた制作プラン、試作、制作結果 |
| [viewer-response-notes](https://github.com/masa-san-jp/viewer-response-notes) | 鑑賞者反応の集計と保守的な評価 |
| [agentic-art-project](https://github.com/masa-san-jp/agentic-art-project) | 検証済みの公開プラン、作品、制作記録のカタログ |

### 利用者の入口

- 制作を始める: [OrchestrationのREADME](https://github.com/masa-san-jp/agentic-art-orchestration#利用者向けの最短ルート)と[agent-runtime-guide](https://github.com/masa-san-jp/agentic-art-orchestration/blob/main/docs/agent-runtime-guide.md)から始める。個別repoを順番に手操作しない。
- 知識を更新する: 更新対象repoのREADME、Issue、schema、validatorを正本として使い、親へ本文をコピーしない。
- Research/Productionを確認する: [agentic-art-research](https://github.com/masa-san-jp/agentic-art-research)と[agentic-art-production](https://github.com/masa-san-jp/agentic-art-production)の各入口を読む。
- 公開プランや作品を見る: [agentic-art-projectのplans/とworks/](https://github.com/masa-san-jp/agentic-art-project)を開く。
- 鑑賞者反応を戻す: [viewer-response-notes](https://github.com/masa-san-jp/viewer-response-notes)で集計し、次回Researchで再検証する。

各repoは独立した正本を持ち、内部log、会話、prompt、credential、PRIVATE_RAW、RESTRICTEDを兄弟repoへ渡しません。

### 根底にある問い

Agentic Artは、生成AIを「古代の芸術家に霊感を与えた精霊のような存在なのか、人間の思考の延長に過ぎないのか」という問いへの態度として、芸術の契機を「精霊や風が運び、人間が受け取って具象化する」と捉えています。全体の背景は[`agentic-art-orchestration`のREADME](https://github.com/masa-san-jp/agentic-art-orchestration#根底にある問い)を正本とし、この姿勢は前身プロジェクト「Vibe Art」（2025年）から受け継がれています。

### このrepoの使い方

このrepoは作品と展示条件に対する鑑賞者反応をaggregate-onlyで保存し、保守的なassessmentを作ります。個人名、自由回答、心理推定、raw asset、credentialは保存せず、検証済みfeedbackだけを次回Researchへ渡します。


## Contracts

- `schemas/viewer-memory.schema.json`: `viewer-memory/v1`, the AAK-12 condition/lineage wrapper around the existing record. See [viewer memory](docs/viewer-memory.md) for owner Git, corrections and scoped retrieval.

- `schemas/viewer-response-record.schema.json`: `viewer-response-record/v1`
- `schemas/viewer-response-assessment.schema.json`: `viewer-response-assessment/v1`
- `schemas/research-signal-export.schema.json`: `research-signal-export/v1`

The record validator enforces the aggregate-only boundary, source commit and
evidence provenance, deterministic deduplication, and append-only uniqueness.
The assessment uses a two-sided Wilson 95% interval: fewer than five measured
observations is `UNKNOWN`; otherwise lower bound `>= 0.60` is `SUPPORTED`, upper
bound `< 0.60` is `CONTRADICTED`, and the remaining cases are `UNKNOWN`.
With no measured sample, two independent external evidence references produce
`EXTERNALLY_SUPPORTED`, which is intentionally not `SUPPORTED`.

## Local commands

```bash
python3 tools/validate.py --check
python3 -m unittest discover -s tests -v
python3 tools/export_signals.py tests/fixtures/viewer-response-records.jsonl --export-id VRSE-fixture --source-commit 0123456789abcdef0123456789abcdef01234567 --output /tmp/viewer-response-export.json
```

Export is deterministic and atomic. Re-running with identical bytes returns
`ALREADY_EXPORTED`; a different existing file returns
`VIEWER-EXPORT-CONFLICT` without overwriting it.

## AP-04 owner verification

The qualified `feat/viewer-response-contracts` source `2c1167c7ce95f0bfa3a2e9f0896bec5836009a87` was verified for AP-04 from orchestration Issue #241. The aggregate-only schemas, opaque provenance, conservative assessments, deterministic export and privacy rejection rules are already present; the verification branch records evidence only. The owner validator, 13-test suite, README export example with a fresh temporary output, and `git diff --check` passed. No names, free text, psychological or medical inference, raw asset, credential, record payload or external write was used.

This is historical evidence for that source, not a qualification of the AAK-12 main tree. See [main reconciliation](docs/main-reconciliation.md) for content provenance and current verification.
