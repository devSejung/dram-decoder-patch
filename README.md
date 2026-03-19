# DRAM Decoder 리팩터 노트

이 패키지는 기존 `decoder.py`를 **동작 보존(behavior-preserving)** 방식으로 리팩터링한 결과물을 다룹니다.

## 목표

- legacy 반환 shape와 key 이름을 유지한다.
- legacy decode 순서와 project-specific 동작을 유지한다.
- LPDDR6 / subchannel 로직을 나중에 더 쉽게 확장할 수 있도록 구조를 정리한다.

## 파일 역할

- `api.py`
  - 백엔드에서 사용하는 안정적인 진입점
- `excel_loader.py`
  - Excel 및 `xlwings` 접근만 담당
- `config_parser.py`
  - 시트 값을 register-like state 배열로 변환
- `decoder_core.py`
  - legacy 알고리즘 순서에 최대한 가깝게 유지한 메인 decode 흐름
- `project_rules.py`
  - ASYM region threshold 같은 프로젝트별 규칙
- `bitops.py`
  - 순수 비트 연산 헬퍼
- `models.py`
  - config / decode 결과 구조 정의

## 안전 원칙

- 검증 중에는 legacy `decoder.py`를 수정하지 않는다.
- 새 경로 결과는 legacy 결과와 비교 검증한 뒤 전환한다.
- project-specific 상수는 명시적으로 재검증되기 전까지 silicon rule로 취급한다.

## LPDDR6 확장 방향

- LPDDR5 흐름은 깨지지 않게 유지한다.
- subchannel selection은 새 decode stage로 추가한다.
- LPDDR6 project-specific 동작은 `project_rules.py` 안에 둔다.
- 백엔드 요구가 공식적으로 바뀌지 않는 한 legacy API shape는 유지한다.

## Resolve Pipeline 리팩터 메모

현재 리팩터는 legacy 동작을 유지하면서 decode 흐름을 더 읽기 쉽게 만드는 데 목적이 있습니다.

현재/목표 stage 순서:

- `resolve_channel(system_addr)`
- `resolve_subchannel(system_addr, ch)` *(LPDDR5 경로에서는 no-op 가능)*
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

## 주소 상태 변화

- `system_addr`: 입력 시스템 주소
- `hole_removed_addr`: ARM hole 제거 후 주소
- `norm_addr`: interleave 정규화 후 주소
- `req_addr`: 필요 시 rank-interleave 제거 후 row/col 계산에 쓰는 주소

## 반드시 지켜야 할 규칙

- channel / asym / tzconfig 는 `system_addr` 기준으로 계산
- interleave 해석은 `hole_removed_addr` 기준
- rank / bank 는 `norm_addr` 기준
- row / col 은 `req_addr` 기준

이 규칙은 behavior-preserving refactor를 유지하면서, 이후 LPDDR6 / subchannel 작업을 더 쉽게 붙이기 위한 기준입니다.

## 저장소 관리 원칙

- 가능하면 behavior-preserving 변경만 다룬다.
- 검증 단계에서는 legacy `decoder.py`를 건드리지 않는다.
- 커밋은 작고 의도가 분명하게 나누는 편이 좋다.
- decode 동작이 바뀌면 이유를 문서화하고 legacy 비교를 먼저 한다.
- readability 변경과 algorithm 변경은 가능하면 분리한다.

## 영어 문서

영문 설명이 필요하면 `README.en.md`를 참고합니다.
