# Inspection Profiles settings UI

Current route:

```text
#/settings/inspection-profiles
```

The authoritative interaction contract is
[Guided Inspection Profiles](guided-inspection-profiles.md). The strict persisted
format remains [Inspection Profiles v1](inspection-profiles-v1.md).

## Page contour

The page keeps the Settings sidebar, compact state summary and searchable catalog.
It does not auto-select an arbitrary note type. Rich catalog entries remain native
buttons and expose note-type name, effective state, friendly detected kind and
field/template counts.

Selecting an unconfigured type creates a deterministic browser-only generated
draft immediately. Opening or switching a clean generated draft is not unsaved
user work. There is no normal-path `Use suggestion` action.

## Basic

Basic is open by default and contains:

1. friendly suggested-setup summary and confidence category;
2. exact Anki field mappings shown through friendly roles;
3. friendly requirements projected over every strict v1 check kind;
4. friendly card-template scope;
5. bounded validation/sample result;
6. one lifecycle-aware primary action.

Basic never displays role slugs, template ordinals or stable check IDs. It never
creates a second persisted model.

## Advanced and tools

Advanced is a native disclosure containing the strict editors and machine-level
identifiers. Profile tools is a separate disclosure containing import, export,
deterministic reset, start empty, disable and delete. These tools do not compete
visually with confirmation.

Hidden Advanced errors are represented outside the collapsed panel. Explicit
failed validation focuses the error summary; links reveal and focus strict controls.

## Persistence and authority

- no autosave;
- no autoconfirm;
- validate v2 before confirmed update v1;
- only `confirmed` and structurally current profiles are authoritative;
- `needs_review` and `disabled` fail closed;
- revision conflicts preserve the local user draft.

## Responsive target

The primary target is desktop/laptop. The catalog/editor split is used at wide
sizes and stacks at 1024 px without horizontal overflow. Advanced remains collapsed
so the normal path is not dominated by the strict editor.

## Verification boundary

C1.5R.6 covers deterministic component/hook/projection tests, backend regression,
typecheck, production build, package validation, canonical non-Docker verification
and a real Chromium light/dark matrix. Docker/real-Anki and owner-private-profile
acceptance belong to C1.5R.7.
