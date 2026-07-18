use serde_json::{Map, Value, json};
use std::collections::{HashMap, HashSet};
use std::env;
use std::fs::File;
use std::io::{BufRead, BufReader};
use std::path::Path;
use thiserror::Error;

const TOLERANCE: f64 = 1e-9;

#[derive(Debug, Error)]
enum OracleError {
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
    #[error("JSON error: {0}")]
    Json(#[from] serde_json::Error),
    #[error("invalid input: {0}")]
    Invalid(String),
}

type Result<T> = std::result::Result<T, OracleError>;

fn object<'a>(value: &'a Value, name: &str) -> Result<&'a Map<String, Value>> {
    value
        .as_object()
        .ok_or_else(|| OracleError::Invalid(format!("{name} must be an object")))
}

fn text<'a>(value: &'a Value, key: &str) -> Result<&'a str> {
    value
        .get(key)
        .and_then(Value::as_str)
        .ok_or_else(|| OracleError::Invalid(format!("{key} must be a string")))
}

fn number(value: &Value, key: &str) -> Result<f64> {
    let result = value
        .get(key)
        .and_then(Value::as_f64)
        .ok_or_else(|| OracleError::Invalid(format!("{key} must be a number")))?;
    if !result.is_finite() {
        return Err(OracleError::Invalid(format!("{key} must be finite")));
    }
    Ok(result)
}

fn integer(value: &Value, key: &str) -> Result<i64> {
    value
        .get(key)
        .and_then(Value::as_i64)
        .ok_or_else(|| OracleError::Invalid(format!("{key} must be an integer")))
}

fn boolean(value: &Value, key: &str) -> Result<bool> {
    value
        .get(key)
        .and_then(Value::as_bool)
        .ok_or_else(|| OracleError::Invalid(format!("{key} must be boolean")))
}

fn array<'a>(value: &'a Value, key: &str) -> Result<&'a Vec<Value>> {
    value
        .get(key)
        .and_then(Value::as_array)
        .ok_or_else(|| OracleError::Invalid(format!("{key} must be an array")))
}

fn pair_table(value: &Value, key: &str, lookup: &str) -> Result<f64> {
    for pair in array(value, key)? {
        let values = pair
            .as_array()
            .ok_or_else(|| OracleError::Invalid(format!("{key} entry must be an array")))?;
        if values.len() == 2 && values[0].as_str() == Some(lookup) {
            return values[1]
                .as_f64()
                .ok_or_else(|| OracleError::Invalid(format!("{key} value must be numeric")));
        }
    }
    Err(OracleError::Invalid(format!(
        "{key} has no value for {lookup}"
    )))
}

fn interpolate(value: f64, anchors: &[Value]) -> Result<f64> {
    let point = |index: usize| -> Result<(f64, f64)> {
        let pair = anchors[index]
            .as_array()
            .ok_or_else(|| OracleError::Invalid("anchor must be an array".into()))?;
        if pair.len() != 2 {
            return Err(OracleError::Invalid("anchor must have two items".into()));
        }
        Ok((
            pair[0]
                .as_f64()
                .ok_or_else(|| OracleError::Invalid("anchor point must be numeric".into()))?,
            pair[1]
                .as_f64()
                .ok_or_else(|| OracleError::Invalid("anchor value must be numeric".into()))?,
        ))
    };
    let first = point(0)?;
    if value <= first.0 {
        return Ok(first.1);
    }
    for index in 1..anchors.len() {
        let left = point(index - 1)?;
        let right = point(index)?;
        if right.0 <= left.0 {
            return Err(OracleError::Invalid("anchor points must increase".into()));
        }
        if value <= right.0 {
            let ratio = (value - left.0) / (right.0 - left.0);
            return Ok(left.1 + ratio * (right.1 - left.1));
        }
    }
    Ok(point(anchors.len() - 1)?.1)
}

fn challenge_curve(retrievability: f64, params: &Value) -> Result<f64> {
    if !(0.0..=1.0).contains(&retrievability) {
        return Err(OracleError::Invalid(
            "retrievability must be in [0, 1]".into(),
        ));
    }
    if retrievability < 0.10 {
        return number(params, "low_retrievability_credit");
    }
    if retrievability >= 0.95 {
        return Ok(0.0);
    }
    interpolate(retrievability, array(params, "challenge_anchors")?)
}

fn delay_credit(drop: f64, params: &Value) -> Result<f64> {
    if drop <= 0.05 {
        return Ok(1.0);
    }
    if drop >= 0.70 {
        return Ok(0.25);
    }
    interpolate(drop, array(params, "delay_credit_anchors")?)
}

fn adjusted_challenge(memory: &Value, params: &Value) -> Result<f64> {
    let actual = match memory.get("retrievability_actual") {
        Some(Value::Number(value)) => value
            .as_f64()
            .ok_or_else(|| OracleError::Invalid("retrievability_actual".into()))?,
        Some(Value::Null) | None => return Ok(0.0),
        _ => {
            return Err(OracleError::Invalid(
                "retrievability_actual must be numeric or null".into(),
            ));
        }
    };
    let actual_credit = challenge_curve(actual, params)?;
    let natural = match memory.get("retrievability_natural_due") {
        Some(Value::Number(value)) => value
            .as_f64()
            .ok_or_else(|| OracleError::Invalid("retrievability_natural_due".into()))?,
        Some(Value::Null) | None => return Ok(actual_credit),
        _ => {
            return Err(OracleError::Invalid(
                "retrievability_natural_due must be numeric or null".into(),
            ));
        }
    };
    if actual >= natural {
        return Ok(actual_credit);
    }
    let due_credit = challenge_curve(natural, params)?;
    let extra = (actual_credit - due_credit).max(0.0);
    Ok(due_credit + extra * delay_credit((natural - actual).max(0.0), params)?)
}

fn memory_gain(memory: &Value, params: &Value) -> Result<f64> {
    let before = memory.get("stability_before").and_then(Value::as_f64);
    let after = memory
        .get("stability_good_counterfactual")
        .and_then(Value::as_f64);
    let (before, after) = match (before, after) {
        (Some(before), Some(after)) => (before, after),
        _ => return Ok(0.0),
    };
    if before <= 0.0 || after <= 0.0 {
        return Err(OracleError::Invalid(
            "stability values must be positive".into(),
        ));
    }
    let raw = (after / before).ln();
    if raw <= 0.10 {
        return Ok(0.0);
    }
    let cap = number(params, "memory_gain_cap")?;
    if raw >= 1.10 {
        return Ok(cap);
    }
    Ok(interpolate(raw, array(params, "memory_gain_anchors")?)?.min(cap))
}

fn episode_reward(episode: &Value, params: &Value) -> Result<Value> {
    let source_key = text(episode, "source_event_key")?;
    let card = text(episode, "card_lineage")?;
    let anki_day = text(episode, "anki_day")?;
    if source_key.trim().is_empty() || card.trim().is_empty() || anki_day.trim().is_empty() {
        return Err(OracleError::Invalid(
            "episode identifiers must not be empty".into(),
        ));
    }
    let outcome = text(episode, "outcome")?;
    if !["again", "hard", "good", "easy", "none"].contains(&outcome) {
        return Err(OracleError::Invalid(format!("unknown outcome: {outcome}")));
    }
    let passed = ["hard", "good", "easy"].contains(&outcome);
    let core = integer(episode, "core_eligibility")?;
    if !(0..=1).contains(&core) {
        return Err(OracleError::Invalid(
            "core_eligibility must be binary".into(),
        ));
    }
    if core == 1 && outcome == "none" {
        return Err(OracleError::Invalid(
            "eligible core episode requires outcome".into(),
        ));
    }
    let bonus = number(episode, "bonus_eligibility")?;
    let validity = number(episode, "response_validity")?;
    if !(0.0..=1.0).contains(&bonus) || !(0.0..=1.0).contains(&validity) {
        return Err(OracleError::Invalid(
            "eligibility values must be in [0, 1]".into(),
        ));
    }
    let baseline = core as f64
        * (number(params, "attempt_credit")?
            + if passed {
                number(params, "outcome_credit")?
            } else {
                0.0
            });
    let memory = episode
        .get("memory")
        .ok_or_else(|| OracleError::Invalid("memory missing".into()))?;
    let challenge = if passed {
        adjusted_challenge(memory, params)?
    } else {
        0.0
    };
    let gain = if passed {
        memory_gain(memory, params)?
    } else {
        0.0
    };
    let confidence = pair_table(params, "confidence_values", text(memory, "confidence")?)?;
    let neutral = number(params, "neutral_context_credit")?;
    let context_credit = if passed && core == 1 {
        neutral + confidence * (challenge + gain - neutral)
    } else {
        0.0
    };
    let effective_bonus = bonus.min(validity);
    let mut context = effective_bonus * context_credit;
    let mut reasons = Vec::<String>::new();
    if passed && core == 1 {
        reasons.push(
            if confidence == 0.0 {
                "neutral_context"
            } else {
                "model_context"
            }
            .into(),
        );
    }
    if effective_bonus < 1.0 && passed && core == 1 {
        reasons.push("bonus_suppressed".into());
    }
    reasons.push(
        if core == 1 {
            "core_eligible"
        } else {
            "core_ineligible"
        }
        .into(),
    );
    let mut total = baseline + context;
    let mut caps = Vec::<String>::new();
    if total >= number(params, "core_episode_cap")? - 1e-12 {
        context = (number(params, "core_episode_cap")? - baseline).max(0.0);
        total = baseline + context;
        caps.push("core_cap_applied".into());
        reasons.push("core_cap_applied".into());
    }
    Ok(json!({
        "rule_version": text(params, "rule_version")?,
        "source_event_key": source_key,
        "baseline": baseline,
        "context": context,
        "total": total,
        "challenge_credit": challenge,
        "memory_gain_credit": gain,
        "core_eligibility": core,
        "bonus_eligibility": effective_bonus,
        "applied_caps": caps,
        "reason_codes": unique(reasons),
    }))
}

fn unique(values: Vec<String>) -> Vec<String> {
    let mut seen = HashSet::new();
    values
        .into_iter()
        .filter(|item| seen.insert(item.clone()))
        .collect()
}

fn volume_credit(qualified: f64, params: &Value) -> Result<(f64, Vec<String>)> {
    let mut total = 0.0;
    let mut reasons = Vec::new();
    for (index, tier) in array(params, "volume_tiers")?.iter().enumerate() {
        let values = tier
            .as_array()
            .ok_or_else(|| OracleError::Invalid("volume tier must be array".into()))?;
        let start = values[0]
            .as_f64()
            .ok_or_else(|| OracleError::Invalid("tier start".into()))?;
        let rate = values[1]
            .as_f64()
            .ok_or_else(|| OracleError::Invalid("tier rate".into()))?;
        let mut amount = (qualified - start).max(0.0);
        if let Some(end) = values[2].as_f64() {
            amount = amount.min(end - start);
        }
        if amount > 0.0 {
            total += rate * amount;
            reasons.push(format!("volume_tier_{}", index + 1));
        }
    }
    let cap = number(params, "volume_cap")?;
    if total > cap {
        total = cap;
        reasons.push("volume_cap_reached".into());
    }
    Ok((total, reasons))
}

fn day_reward(day: &Value, params: &Value) -> Result<Value> {
    let anki_day = text(day, "anki_day")?;
    let undone: HashSet<String> = array(day, "undone_source_event_keys")?
        .iter()
        .map(|item| item.as_str().unwrap_or_default().to_string())
        .collect();
    let mut seen_sources = HashSet::<String>::new();
    let mut seen_cards = HashSet::<String>::new();
    let mut episode_results = Vec::<Value>::new();
    let mut reasons = Vec::<String>::new();
    let mut routed_supplemental = 0.0;
    for episode in array(day, "episodes")? {
        if text(episode, "anki_day")? != anki_day {
            return Err(OracleError::Invalid("episode anki_day mismatch".into()));
        }
        let source_key = text(episode, "source_event_key")?.to_string();
        let card_day = format!("{}\0{}", text(episode, "card_lineage")?, anki_day);
        let mut effective = episode.clone();
        let (decision_reason, no_op, supplemental) = if undone.contains(&source_key) {
            ("undone", true, false)
        } else if seen_sources.contains(&source_key) {
            ("duplicate_source_event", true, false)
        } else if boolean(episode, "administrative")?
            || text(episode, "role")? == "administrative"
            || text(episode, "source")? == "manual_operation"
        {
            ("administrative_zero", true, false)
        } else if boolean(episode, "preview_without_rescheduling")?
            || text(episode, "source")? == "filtered_preview"
        {
            ("preview_zero", true, false)
        } else if boolean(episode, "forced_due")? || text(episode, "due_relation")? == "forced_due"
        {
            ("forced_due_supplemental", true, true)
        } else if text(episode, "eligibility_class")? == "route_to_learn" {
            ("routed_to_learn", true, false)
        } else if text(episode, "eligibility_class")? != "core" {
            ("core_ineligible", true, false)
        } else if seen_cards.contains(&card_day) {
            ("duplicate_card_day", true, false)
        } else {
            ("core_eligible", false, false)
        };
        reasons.push(decision_reason.into());
        seen_sources.insert(source_key);
        if supplemental {
            routed_supplemental += number(episode, "supplemental_units")?;
            continue;
        }
        if no_op {
            continue;
        }
        seen_cards.insert(card_day);
        let map = effective
            .as_object_mut()
            .ok_or_else(|| OracleError::Invalid("episode object".into()))?;
        map.insert("eligibility_class".into(), json!("core"));
        let result = episode_reward(&effective, params)?;
        episode_results.push(result);
    }
    let sum_field = |key: &str| -> f64 {
        episode_results
            .iter()
            .filter_map(|item| item[key].as_f64())
            .sum()
    };
    let core_baseline = sum_field("baseline");
    let core_context = sum_field("context");
    let qualified = core_baseline;
    let mut support_by_parent = HashMap::<String, f64>::new();
    for support in array(day, "support_events")? {
        let source = text(support, "source_event_key")?.to_string();
        if seen_sources.contains(&source) {
            reasons.push("duplicate_source_event".into());
            continue;
        }
        seen_sources.insert(source.clone());
        let parent = text(support, "parent_episode_key")?;
        if undone.contains(&source) || undone.contains(parent) {
            reasons.push("undone".into());
            continue;
        }
        let units = pair_table(params, "support_values", text(support, "kind")?)?;
        *support_by_parent.entry(parent.into()).or_insert(0.0) += units;
    }
    let episode_support_cap = number(params, "support_episode_cap")?;
    let mut raw_support = 0.0;
    let mut applied_caps = Vec::<String>::new();
    for units in support_by_parent.values() {
        raw_support += units.min(episode_support_cap);
        if *units > episode_support_cap {
            applied_caps.push("support_episode_cap".into());
            reasons.push("support_episode_cap".into());
        }
    }
    let support_cap = number(params, "support_day_cap")?.min(
        number(params, "support_day_floor")?
            .max(number(params, "support_day_rate")? * core_baseline),
    );
    let capped_support = raw_support.min(support_cap);
    if raw_support > capped_support {
        applied_caps.push("support_day_cap".into());
        reasons.push("support_day_cap".into());
    }
    let mut raw_supplemental = routed_supplemental;
    for supplemental in array(day, "supplemental_events")? {
        let source = text(supplemental, "source_event_key")?.to_string();
        if seen_sources.contains(&source) {
            reasons.push("duplicate_source_event".into());
            continue;
        }
        seen_sources.insert(source.clone());
        if undone.contains(&source) || !boolean(supplemental, "permanent_eligible")? {
            if undone.contains(&source) {
                reasons.push("undone".into());
            }
            continue;
        }
        raw_supplemental += number(supplemental, "units")?;
    }
    let supplemental_cap = number(params, "supplemental_day_cap")?
        .min(number(params, "supplemental_day_rate")? * core_baseline);
    let capped_supplemental = raw_supplemental.min(supplemental_cap);
    if raw_supplemental > capped_supplemental {
        applied_caps.push("supplemental_day_cap".into());
        reasons.push("supplemental_day_cap".into());
    }
    let (volume, volume_reasons) = volume_credit(qualified, params)?;
    for reason in &volume_reasons {
        if reason == "volume_cap_reached" {
            applied_caps.push(reason.clone());
        }
    }
    reasons.extend(volume_reasons);
    let workload = day
        .get("workload")
        .ok_or_else(|| OracleError::Invalid("workload missing".into()))?;
    let mut status = text(workload, "status")?;
    if !boolean(workload, "snapshot_confident")? {
        status = "snapshot_uncertain";
    }
    let factor = pair_table(params, "completion_factors", status)?;
    let completion = factor
        * number(params, "completion_cap")?.min(number(params, "completion_rate")? * qualified);
    match status {
        "collection_cleared"
        | "scope_cleared"
        | "configured_limit_reached"
        | "zero_due"
        | "snapshot_uncertain" => reasons.push(status.into()),
        _ => {}
    }
    let total =
        core_baseline + core_context + capped_support + capped_supplemental + volume + completion;
    let contribution = if qualified <= 0.0 {
        "review_none"
    } else if qualified >= 25.0
        || (qualified >= 5.0
            && [
                "collection_cleared",
                "scope_cleared",
                "configured_limit_reached",
            ]
            .contains(&status))
    {
        "review_full"
    } else if qualified >= 10.0 {
        "review_substantive"
    } else {
        "review_light"
    };
    Ok(json!({
        "rule_version": text(params, "rule_version")?,
        "anki_day": anki_day,
        "core_baseline": core_baseline,
        "core_context": core_context,
        "raw_support": raw_support,
        "capped_support": capped_support,
        "support_cap": support_cap,
        "raw_supplemental": raw_supplemental,
        "capped_supplemental": capped_supplemental,
        "supplemental_cap": supplemental_cap,
        "qualified_volume": qualified,
        "volume_credit": volume,
        "completion_credit": completion,
        "total": total,
        "contribution_band": contribution,
        "applied_caps": unique(applied_caps),
        "reason_codes": unique(reasons),
        "episode_breakdowns": episode_results,
    }))
}

fn compare_expected(actual: &Value, expected: &Value) -> Result<()> {
    let expected_map = object(expected, "expected")?;
    for (key, expected_value) in expected_map {
        let actual_value = actual
            .get(key)
            .ok_or_else(|| OracleError::Invalid(format!("missing actual field {key}")))?;
        match (actual_value.as_f64(), expected_value.as_f64()) {
            (Some(left), Some(right)) if (left - right).abs() <= TOLERANCE => {}
            _ if actual_value == expected_value => {}
            _ => {
                return Err(OracleError::Invalid(format!(
                    "expected mismatch at {key}: expected {expected_value}, got {actual_value}"
                )));
            }
        }
    }
    Ok(())
}

fn evaluate_line(line: &str, verify: bool) -> Result<Value> {
    let case: Value = serde_json::from_str(line)?;
    let case_id = text(&case, "case_id")?;
    let kind = text(&case, "kind")?;
    let input = case
        .get("input")
        .ok_or_else(|| OracleError::Invalid("input missing".into()))?;
    let params = case
        .get("parameters")
        .ok_or_else(|| OracleError::Invalid("parameters missing".into()))?;
    let result = match kind {
        "episode" => episode_reward(input, params)?,
        "day" => day_reward(input, params)?,
        _ => return Err(OracleError::Invalid(format!("unsupported kind: {kind}"))),
    };
    if verify {
        compare_expected(
            &result,
            case.get("expected")
                .ok_or_else(|| OracleError::Invalid("expected missing".into()))?,
        )?;
    }
    Ok(json!({"case_id": case_id, "ok": true, "result": result}))
}

fn run_file(command: &str, path: &Path) -> Result<()> {
    let verify = command == "verify-golden";
    let reader = BufReader::new(File::open(path)?);
    let mut failures = 0;
    for line in reader.lines() {
        let line = line?;
        if line.trim().is_empty() {
            continue;
        }
        match evaluate_line(&line, verify) {
            Ok(output) => println!("{}", serde_json::to_string(&output)?),
            Err(error) => {
                failures += 1;
                let case_id = serde_json::from_str::<Value>(&line)
                    .ok()
                    .and_then(|value| {
                        value
                            .get("case_id")
                            .and_then(Value::as_str)
                            .map(str::to_owned)
                    })
                    .unwrap_or_else(|| "unknown".into());
                println!(
                    "{}",
                    json!({"case_id": case_id, "ok": false, "error": error.to_string()})
                );
            }
        }
    }
    if failures > 0 {
        return Err(OracleError::Invalid(format!(
            "{failures} verification case(s) failed"
        )));
    }
    Ok(())
}

fn run_fsrs_reference(path: &Path) -> Result<()> {
    let payload: Value = serde_json::from_reader(File::open(path)?)?;
    let fsrs = FSRS::default();
    let mut trajectories = Vec::new();
    for trajectory in array(&payload, "trajectories")? {
        let trajectory_id = text(trajectory, "trajectory_id")?;
        if text(trajectory, "mode")? == "no_fsrs" {
            trajectories.push(json!({
                "trajectory_id": trajectory_id,
                "mode": "no_fsrs",
                "steps": [],
            }));
            continue;
        }
        let desired_retention = number(trajectory, "desired_retention")? as f32;
        let mut state: Option<MemoryState> = None;
        let mut previous_day = 0_u32;
        let mut steps = Vec::new();
        for (index, review) in array(trajectory, "reviews")?.iter().enumerate() {
            let day_i64 = integer(review, "day")?;
            if day_i64 < 0 {
                return Err(OracleError::Invalid(
                    "FSRS review day must be non-negative".into(),
                ));
            }
            let day = day_i64 as u32;
            if index > 0 && day < previous_day {
                return Err(OracleError::Invalid(
                    "FSRS review days must be nondecreasing".into(),
                ));
            }
            let elapsed = if index == 0 { day } else { day - previous_day };
            let retrievability = state
                .map(|memory| current_retrievability(memory, elapsed as f32, FSRS6_DEFAULT_DECAY))
                .unwrap_or(0.0);
            let next = fsrs
                .next_states(state, desired_retention, elapsed)
                .map_err(|error| OracleError::Invalid(format!("FSRS next_states: {error}")))?;
            let selected = match text(review, "rating")? {
                "Again" => &next.again,
                "Hard" => &next.hard,
                "Good" => &next.good,
                "Easy" => &next.easy,
                rating => {
                    return Err(OracleError::Invalid(format!(
                        "unknown FSRS rating: {rating}"
                    )));
                }
            };
            steps.push(json!({
                "day": day,
                "rating": text(review, "rating")?,
                "retrievability_before": retrievability,
                "stability": selected.memory.stability,
                "difficulty": selected.memory.difficulty,
                "scheduled_interval_days": selected.interval,
                "counterfactual_good_stability": next.good.memory.stability,
            }));
            state = Some(selected.memory);
            previous_day = day;
        }
        trajectories.push(json!({
            "trajectory_id": trajectory_id,
            "mode": "fsrs",
            "desired_retention": desired_retention,
            "steps": steps,
        }));
    }
    println!(
        "{}",
        serde_json::to_string(&json!({
            "implementation": "fsrs-rs",
            "crate_version": "6.6.1",
            "trajectories": trajectories,
        }))?
    );
    Ok(())
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() != 3
        || !["verify-golden", "evaluate-jsonl", "fsrs-reference"].contains(&args[1].as_str())
    {
        eprintln!(
            "usage: gamification-rust-oracle <verify-golden|evaluate-jsonl|fsrs-reference> <path>"
        );
        std::process::exit(2);
    }
    let result = if args[1] == "fsrs-reference" {
        run_fsrs_reference(Path::new(&args[2]))
    } else {
        run_file(&args[1], Path::new(&args[2]))
    };
    if let Err(error) = result {
        eprintln!("{error}");
        std::process::exit(1);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn unique_preserves_first_occurrence() {
        assert_eq!(
            unique(vec!["a".into(), "b".into(), "a".into()]),
            vec!["a", "b"]
        );
    }

    #[test]
    fn tolerance_matches_contract() {
        assert!((1.0_f64 - (1.0 + 5e-10)).abs() <= TOLERANCE);
    }
}
use fsrs::{FSRS, FSRS6_DEFAULT_DECAY, MemoryState, current_retrievability};
