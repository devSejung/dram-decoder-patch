# DRAM Decoder Refactor Notes

This package is a behavior-preserving refactor of `decoder.py`.

## Goal

- Keep the legacy return shape and key names unchanged.
- Preserve the legacy decode order and project-specific behavior.
- Make the code easier to maintain and extend for LPDDR6 and subchannel logic.

## File Roles

- `api.py`
  Stable entry points for backend use.
- `excel_loader.py`
  Excel and `xlwings` access only.
- `config_parser.py`
  Converts sheet values into register-like state arrays.
- `decoder_core.py`
  Main decode flow, kept close to the legacy algorithm order.
- `project_rules.py`
  Project-specific rules such as ASYM region thresholds.
- `bitops.py`
  Pure bit helper functions.
- `models.py`
  Named structures for config and decode results.

## Safety Rules

- Do not edit `decoder.py` while validating the new path.
- Compare new results against legacy results before switching backend traffic.
- Treat project-specific constants as silicon rules unless they are explicitly re-validated.

## LPDDR6 Extension Direction

- Add subchannel selection as a new decode stage without changing LPDDR5 flow.
- Keep project-specific LPDDR6 behavior inside `project_rules.py`.
- Preserve the legacy API shape unless backend requirements formally change.

## Resolve Pipeline Refactor Notes

The current refactor keeps legacy behavior intact while making the decode flow easier to read and maintain.

Planned/implemented stage order:

- `resolve_channel(system_addr)`
- `resolve_subchannel(system_addr, ch)` *(LPDDR5 path can remain no-op)*
- `select_tzconfig(ch, asym_region)`
- `remove_address_hole(system_addr)`
- `resolve_interleave(hole_removed_addr, tzcfg)`
- `normalize_addr(hole_removed_addr, intlv)`
- `resolve_rank(norm_addr, tzcfg)`
- `resolve_bank(norm_addr, rank, addr_mode)`
- `resolve_req_addr(norm_addr, rank_hit, tzcfg)`
- `resolve_row(req_addr, addr_mode)`
- `resolve_col(req_addr, bank_layout)`
- `build_legacy_result(...)`

Address lifecycle:

- `system_addr`: original input address
- `hole_removed_addr`: address after ARM hole removal
- `norm_addr`: address after interleave normalization
- `req_addr`: address used for row/column resolution after optional rank-interleave removal

Safety invariants:

- channel / asym / tzconfig are resolved from `system_addr`
- interleave resolution is based on `hole_removed_addr`
- rank / bank are resolved from `norm_addr`
- row / col are resolved from `req_addr`

These rules are intended to keep the refactor behavior-preserving while making future LPDDR6/subchannel work easier to add.
