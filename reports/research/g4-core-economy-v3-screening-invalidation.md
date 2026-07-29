# G4 core economy — invalidation G4.3 v3 screening

## Статус

```text
protocol version: 3
publication commit: aa8d119ad5896267f46d9eb644392de11c0e32a2
evaluator implementation commit: a0283a4945ab4201c0cda284f60b3c2ad7c118c4
screening execution: COMPLETE
result disposition: INVALIDATED_NOT_DECISION_EVIDENCE
replacement required: G4.3 v4
production integration: PROHIBITED
```

Первый полный result access был выполнен только после publication checkpoint v3. Run обработал 1275 из 1275 frozen rows, не имел missing, extra или duplicate rows и прошёл detached byte-identical recomputation.

## Invalidated identities

```text
result artifact digest: 91fc19ddcde96e5a6699b53abedc1871d4b5b547ec292ecde23980e74d284208
result set digest: 7501d5f3248b468dec6d8c338ca019d0543400b7696eb77b24dbb042d2448612
gates evaluated: 3952
metrics evaluated: 3556
```

Raw invalidated result artifacts не публикуются как repository evidence и не используются для candidate comparison или final decision.

## Причины invalidation

V3 обнаружил substantive pre-result contract defects:

- некоторые scenario rows объявляли applicable gate без всех его `required_metric_ids`; пример: `SC-DAILY-REVIEW-5` содержал `HG-NO-SESSION-SPLIT-GAIN`, но не `M-SESSION-SPLIT-DELTA`;
- abrupt-control expected outcomes зависели от наличия positive context, а не от фактического predicate violation на uncertainty-bearing events;
- evaluator marginal probe для combined-cap control мог начинаться на самой global boundary даже тогда, когда scenario predicate требовал probe ниже boundary.

Эти дефекты нельзя исправлять in-place после result access. V3 artifacts остаются immutable. V4 обязан исправить contract linkage и expected rules до нового publication commit; после него выполняется полный replacement screening.

## Evidence boundary

```text
v1 results: NOT_AVAILABLE
v2 results: NOT_AVAILABLE
v3 results: INVALIDATED_NOT_DECISION_EVIDENCE
v4 results: NOT_AVAILABLE
real user data: false
winner selected: false
G5: NOT STARTED
G6: NOT STARTED
```
