# Rust oracle JSONL contract v0.1

Each UTF-8 JSONL row contains `case_id`, `kind`, a fully normalized `input`, and
a full normalized `parameters` snapshot. `kind` is `episode` or `day`.

```powershell
cargo run --manifest-path rust-oracle/Cargo.toml -- verify-golden <golden-corpus.jsonl>
cargo run --manifest-path rust-oracle/Cargo.toml -- evaluate-jsonl <differential-inputs.jsonl>
```

`verify-golden` also requires an `expected` object and compares its declared
fields at tolerance `1e-9`. Both commands write one result row per case to stdout,
write diagnostics to stderr, and return non-zero if any input is invalid or any
golden expectation mismatches.

The Python `verify-rust-oracle` command prepares the full corpus in an isolated
temporary directory from committed sources. The deterministic corpus comprises
31 golden cases, every day from all 26 scenario definitions, explicit threshold
triplets, all Stage 5B.3 survivors, fixed property-edge cases, and invalid-input
parity cases. Generated JSONL and reports are gitignored local artifacts; source
IDs and counts are included in the report manifest.

Python and Rust share data contracts, enum strings, units, rule versions,
parameter snapshots, tolerance, and reason-code vocabulary. They do not share
formula source code or a native process boundary.
