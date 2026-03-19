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
