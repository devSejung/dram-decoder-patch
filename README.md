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

## `api.py`의 `decode()` 함수 설명

`decode(project_code, mem_config, system_addrs)`는 외부에서 사용하는 공식 진입점입니다.
이 함수 자체는 복잡한 비트 연산을 직접 하지 않고, **엑셀 설정을 읽고 decode에 필요한 context를 구성한 뒤 `decode_addresses()`로 넘기는 역할**을 합니다.

순서는 다음과 같습니다.

1. `ExcelConfigRepository`를 가져옵니다.
2. `excel_data` 딕셔너리를 준비합니다.
3. `mem_config`를 정수로 변환합니다.
4. `get_channel_config_info(project_code)`로 채널/해시 관련 공통 정보를 읽습니다.
5. `make_project_df(project_code)`로 프로젝트 시트를 DataFrame 형태로 읽습니다.
6. 위 정보를 묶어 `DecodeContext`를 만듭니다.
7. `decode_addresses(context, system_addrs)`를 호출합니다.
8. 최종적으로 `(error, result, excel_data)` 형태로 반환합니다.

즉 `decode()`는 **설정 준비 + context 생성 + 내부 decode 호출 래퍼**라고 보면 됩니다.

## `decoder_core.py`의 `decode_addresses()` 단계별 설명

`decode_addresses()`는 실제 주소 해석 본체입니다. 각 시스템 주소마다 아래 파이프라인을 순서대로 수행합니다.

### 1. 입력 주소 정리

- 공백 제거
- 중복 제거

### 2. 엑셀/설정 정보 준비

- `excel_data["ch_info"]`에 채널 공통 정보 저장
- `excel_data["tz"]`에 선택된 config column 값 저장
- `build_register_state()`로 빈 register-like state 생성
- `load_primary_config()` / `load_asym_config()`로 엑셀 값을 내부 계산용 state에 적재

### 3. `system_addr`

입력 16진 주소 문자열을 정수로 변환한 원본 시스템 주소입니다.

### 4. channel 계산

- `CH_Bit*Hash` 마스크로 주소 비트를 고름
- `parity()`로 각 채널 선택 비트 계산
- 최종 `CH` 생성

이 단계는 **해시 기반 분산 선택**입니다.

### 5. ASYM region / `tzconfig` 선택

- 비대칭 구성일 경우 `project_rules.py`의 threshold 규칙으로 `asym_region` 판정
- 채널 위치에 따라 사용할 TZ config(0 또는 1) 결정

즉 같은 프로젝트라도 채널에 따라 다른 register 세트를 참조할 수 있습니다.

### 6. `hole_removed_addr`

ARM address map의 hole 구간을 제거해서, 주소를 연속 공간처럼 다룰 수 있도록 만든 주소입니다.

### 7. interleave 판정 및 `norm_addr`

- `hole_removed_addr`가 어느 interleave region에 속하는지 판정
- `intlv_en`, `intlv_sel`, `intlv_granule` 계산
- interleave 선택용 비트를 제거해서 `norm_addr` 생성

`norm_addr`는 **rank/bank 계산을 위한 정규화 주소**입니다.

### 8. rank 계산

`norm_addr`가 어느 rank region(Base/Mask)에 속하는지 비교해서 rank를 정합니다.

이 단계는 해시 기반이 아니라 **영역 hit 판정 기반**입니다.

### 9. bank 계산

- `AddrMapMode`로 bank mode(`bank16opt4` / `bank16opt1`) 결정
- `Bank*HashBitEn`과 주소 비트를 조합해 parity/XOR로 bank 계산
- `bank -> BankGroup / Bank`로 분리

즉 bank는 channel과 비슷하게 **해시 기반 선택**입니다.

### 10. `req_addr`

2-rank interleave가 켜져 있으면 rank select 비트를 제거한 새 주소를 만들고,
아니면 `norm_addr`를 그대로 사용합니다.

이 주소는 **row/col 계산 전용 내부 주소**입니다.

### 11. row 계산

`req_addr`와 `AddrMapMode`를 기준으로 row에 해당하는 비트 구간을 잘라냅니다.

### 12. col / burst 계산

`req_addr`와 bank mode를 기준으로 column 비트를 조합한 뒤,
- 상위 부분은 `Col`
- 하위 4비트는 `Bur`
로 나눕니다.

### 13. legacy 결과 조립

최종적으로 아래 항목을 legacy shape 그대로 dict로 반환합니다.

- `Physical_addr`
- `Normalized_addr`
- `CH`
- `Rank`
- `BankGroup`
- `Bank`
- `Row`
- `Col`
- `Bur`

## 주소 상태 변화 요약

이 프로젝트에서 주소는 단계별로 아래처럼 변합니다.

1. `system_addr`
   - 원본 시스템 주소
2. `hole_removed_addr`
   - ARM hole 제거 후 주소
3. `norm_addr`
   - interleave 제거 후 주소
4. `req_addr`
   - rank interleave 제거 후 row/col 계산용 주소

## 꼭 기억할 기준

- `channel / asym / tzconfig` → `system_addr` 기준
- `interleave` → `hole_removed_addr` 기준
- `rank / bank` → `norm_addr` 기준
- `row / col` → `req_addr` 기준

이 기준을 섞어 보면 디버깅이 매우 어려워집니다.
