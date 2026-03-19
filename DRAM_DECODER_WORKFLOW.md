# DRAM Decoder 워크플로우 및 유지보수 가이드

## 문서 목적

이 문서는 현재 [`decoder.py`](/c:/Users/sejun/OneDrive/바탕 화면/Project/workspace/decoder.py)가 어떤 순서로 동작하는지, 각 단계가 무엇을 의미하는지, 디버깅할 때 무엇을 먼저 확인해야 하는지, 그리고 앞으로 LPDDR6/서브채널 대응을 어떤 구조로 가져가면 안전한지를 정리한 문서입니다.

이 문서는 `구조 설명 + 유지보수 가이드 + 확장 제안` 문서입니다.

- 현재 기준 구현은 [`decoder.py`](/c:/Users/sejun/OneDrive/바탕 화면/Project/workspace/decoder.py)입니다.
- 리팩토링 초안은 [`dram_decoder`](/c:/Users/sejun/OneDrive/바탕 화면/Project/workspace/dram_decoder) 아래에 있습니다.
- 이 워크스페이스에는 `SMC_TZConfig.xlsx`가 없으므로, 실제 운영 설정 기준의 런타임 동등성 검증은 아직 끝나지 않았습니다.
- 따라서 이 문서의 설명은 `코드 해석과 구조 제안`으로 받아들이는 것이 맞습니다.

## 이 코드를 한 줄로 설명하면

이 코드는 **시스템 주소를 DRAM 내부 좌표로 해석하는 백엔드 디코더**입니다.

입력:

- `system_addr`
- `project_code`
- `mem_config`

출력:

- `CH`
- `Rank`
- `BankGroup`
- `Bank`
- `Row`
- `Col`
- `Bur`

중요한 점은, 이 코드는 단순 계산기가 아니라는 것입니다.

- 코드 안에 들어있는 비트 해석 알고리즘
- Excel에 들어있는 프로젝트별 설정값
- 일부 프로젝트별 하드코딩 규칙

이 세 가지가 합쳐져서 최종 결과를 만듭니다.

즉 실제 동작은 아래처럼 이해해야 합니다.

```text
system address
+ project별 Excel 설정값
+ project별 예외 규칙
= 최종 DRAM 좌표
```

## 먼저 알아야 하는 DRAM 기본 개념

이 섹션은 "코드는 읽겠는데 DRAM 주소 체계가 아직 완전히 익숙하지 않다"는 상황을 기준으로 적었습니다.

## 1. Channel

`Channel`은 메모리 컨트롤러가 메모리에 접근하는 큰 단위 경로 중 하나입니다.

대충 감각적으로 보면:

- Channel이 많을수록 동시에 더 많이 분산해서 접근할 수 있습니다.
- controller는 주소를 여러 Channel에 나눠 보내서 대역폭과 병렬성을 높입니다.

이 코드에서 `CH`는 최종적으로 선택된 channel 번호입니다.

## 2. Rank

`Rank`는 DRAM 장치 묶음 단위라고 이해하면 됩니다.

실무적으로는 보통:

- 같은 channel 안에서 여러 rank가 존재할 수 있고
- 주소에 따라 rank0 또는 rank1로 나뉩니다

이 코드에서 `Rank`는 최종 rank 선택 결과입니다.

## 3. BankGroup / Bank

DRAM 내부는 단순히 한 덩어리가 아니라 더 잘게 나뉘어 있습니다.

- BankGroup은 bank들을 상위에서 묶는 단위
- Bank는 실제로 활성화되는 내부 메모리 뱅크

즉:

```text
Channel
  -> Rank
    -> BankGroup
      -> Bank
        -> Row / Column
```

처럼 생각하면 이해가 쉽습니다.

## 4. Row / Column

DRAM은 보통 2차원 배열처럼 생각하면 편합니다.

- `Row`: 큰 줄 단위
- `Column`: 그 row 안에서의 위치

읽기/쓰기는 대체로:

1. Row를 열고
2. 그 안에서 Column을 접근

하는 흐름으로 이해할 수 있습니다.

그래서 row가 틀리면 완전히 다른 영역을 보고 있는 것이고, column이 틀리면 같은 row 안에서 다른 위치를 보고 있는 것입니다.

## 5. Burst

`Burst`는 column 하위 비트 쪽에서 연속 전송 단위를 나타내는 개념으로 이해하면 됩니다.

이 코드에서는:

- raw column 값을 만든 뒤
- 하위 일부 비트를 `Bur`
- 나머지를 `Col`

로 분리합니다.

즉 `Bur`는 "column의 가장 하위 전송 오프셋"처럼 보면 됩니다.

## 6. Interleave

`Interleave`는 주소를 단순히 순서대로 한 곳에 쌓지 않고, 여러 channel/rank/bank 쪽으로 분산시키는 정책입니다.

왜 필요하냐면:

- 한 자원으로 몰리지 않게 하고
- 병렬성을 높이고
- 대역폭 효율을 높이기 위해서입니다.

하지만 interleave를 쓰면 시스템 주소와 실제 DRAM 내부 주소가 바로 대응되지 않기 때문에, decoder는 중간에 interleave 비트를 제거하는 과정을 거칩니다.

## 7. Address Hole

시스템 주소 공간은 항상 DRAM이 연속으로 배치된 것처럼 보이지 않습니다.
중간에 hole이 있을 수 있습니다.

이 코드에서는 먼저 ARM address map 관점의 hole을 제거한 뒤, 그다음에 DRAM 해석을 진행합니다.

즉 입력 주소를 바로 믿으면 안 됩니다.

## 8. Hash

이 코드에서 `hash`는 암호학 해시가 아니라, 여러 주소 비트를 섞어서 특정 선택 비트를 만드는 방식입니다.

예를 들면:

- 여러 주소 비트의 parity를 구해서 channel bit를 만들거나
- 여러 주소 비트를 섞어서 bank bit를 만들 수 있습니다

즉 "주소를 단순 선형으로 자르지 않고, 분산을 위해 섞는 것"이라고 이해하면 됩니다.

## 이 코드를 이해할 때 가장 중요한 전제

이 코드에서는 입력 주소 하나가 그대로 최종 row/column이 되는 것이 아닙니다.

중간에 주소 상태가 여러 번 바뀝니다.

대표적으로:

- `system_addr`
- `hole_removed_addr`
- `Normalized_addr`
- `req_addr`

이 네 주소는 서로 다를 수 있습니다.

이걸 같은 주소라고 생각하면 디버깅이 꼬입니다.

## 전체 흐름 요약

```text
입력 주소(system_addr)
    |
    v
프로젝트/메모리 설정값 로딩
    |
    v
채널 해시 계산
    |
    v
ASYM 영역 판정
    |
    v
TZ config 선택
    |
    v
ARM address hole 제거
    |
    v
interleave region 판정
    |
    v
interleave 비트 제거 -> Normalized_addr
    |
    v
rank region hit 판정
    |
    v
bank mode 판정
    |
    v
bank hash 계산 -> BankGroup / Bank
    |
    v
필요시 rank interleave 제거 -> req_addr
    |
    v
row 계산
    |
    v
column / burst 계산
    |
    v
결과 dict 반환
```

## 이 코드에서 헷갈리기 쉬운 핵심 개념

## 1. `system_addr`는 바로 DRAM 주소가 아니다

입력으로 들어오는 주소는 CPU/시스템 관점의 주소입니다.

하지만 controller는 이 주소를 그대로 row/column으로 해석하지 않습니다.
중간에 다음 변환이 들어갑니다.

- address hole 제거
- channel interleave 제거
- 필요시 rank interleave 제거

즉 최종 row/column을 뽑는 주소는 입력 주소와 다를 수 있습니다.

## 2. 채널(CH)은 단순히 주소 한 비트로 정해지지 않는다

이 코드에서는 `CH = addr[n]` 같은 방식이 아닙니다.

대신:

- 여러 주소 비트를 선택하고
- parity를 구하고
- 그 결과 비트들을 조합해서 channel을 만듭니다

즉 주소 비트를 해시처럼 섞어서 channel을 고른다고 보는 게 맞습니다.

## 3. `Normalized_addr`는 디버깅의 중심이다

`Normalized_addr`는 interleave 관련 비트를 제거한 주소입니다.

실무적으로는:

- rank가 왜 틀렸는지
- bank가 왜 틀렸는지
- row/col이 왜 틀렸는지

대부분이 이 주소가 맞는지부터 봐야 합니다.

## 4. `req_addr`는 `Normalized_addr`와 다를 수 있다

2-rank interleave가 걸려 있으면 rank select용 비트를 한 번 더 제거합니다.

그 결과가 `req_addr`입니다.

즉 row/column 계산은 항상 `Normalized_addr` 기준이 아니라, 경우에 따라 `req_addr` 기준입니다.

## 5. `bank hash`는 JEDEC 일반 공식이라기보다 controller 정책에 가깝다

이 코드에서 `bank hash`는 단순히 "bank bit를 어디서 자르느냐"가 아닙니다.

실제 의미는:

- 일부 주소 비트를 mask로 선택하고
- 그 parity를 구한 뒤
- 특정 직접 비트와 XOR해서
- 최종 bank bit를 만든다

입니다.

즉 bank 선택을 고르게 분산시키기 위한 controller 정책이라고 보는 것이 맞습니다.

## 6. Excel 값은 단순 설정이 아니라 decode rule 그 자체다

`CH_Bit*Hash`, `BaseAddr`, `BaseMask`, `IntlvBase`, `AddrMapMode` 같은 값은 단순 옵션이 아닙니다.

이 값들이 곧:

- channel 선택 규칙
- rank region 규칙
- interleave 해제 규칙
- row/column 해석 규칙

을 결정합니다.

즉 Excel은 참고용 테이블이 아니라 **실제 decode rule의 일부**입니다.

## 주요 함수 역할

## 비트 유틸 함수

[`decoder.py`](/c:/Users/sejun/OneDrive/바탕 화면/Project/workspace/decoder.py) 안의 아래 함수들은 전체 해석 로직의 기초입니다.

- `cut_bits(num, msb, lsb)`
  지정한 비트 구간을 잘라냅니다.
- `inv_bits(num, bitlength)`
  제한된 비트 폭 안에서 마스크를 반전시킵니다.
- `parity(x)`
  set bit 개수의 홀짝을 계산합니다.
- `find_zero_lsb(num)`
  trailing one 다음에 처음 나오는 0의 위치를 찾습니다.

이 함수들은 짧지만 매우 중요합니다. 여기 동작이 바뀌면 전체 decoder가 틀어질 수 있습니다.

## Excel/설정 접근 함수

- `get_project_list()`
- `make_project_df(project_name)`
- `get_chConfig_info(project_code)`
- `get_memory_configuration_list(project_code)`

이 함수들은 Excel 시트 값을 runtime에서 쓰는 설정 구조로 바꾸는 역할을 합니다.

## 메인 함수

- `decode(project_code, mem_config, system_addrs)`

실제 주소 해석은 이 함수가 담당합니다.

## 상세 워크플로우

## 1. 프로젝트 설정값 로딩

먼저 두 종류 설정을 읽습니다.

- `CHConfig` 시트에서 가져오는 project 공통 channel/hash 정보
- project별 시트에서 가져오는 특정 memory configuration 정보

대표적으로 읽는 값:

- `CH_num`
- `CHASYM`
- `CH_Bit2Hash`, `CH_Bit1Hash`, `CH_Bit0Hash`
- `Bank3HashBitEn` ~ `Bank0HashBitEn`
- `BaseAddr*`, `BaseMask*`
- `ExtBaseAddr*`, `ExtBaseMask*`
- `IntlvBaseAddr*`, `IntlvBaseMask*`
- `ExtIntlvBaseAddr*`, `ExtIntlvBaseMask*`
- `AddrMapMode`
- `TzSpare`

이 값들은 사실상 register-like decode parameter입니다.

## 2. 채널 해시 계산

코드는 대략 다음을 계산합니다.

```text
CH_Bit2 = parity(system_addr & CH_Bit2Hash)
CH_Bit1 = parity(system_addr & CH_Bit1Hash)
CH_Bit0 = parity(system_addr & CH_Bit0Hash)
CH = (CH_Bit2*4 + CH_Bit1*2 + CH_Bit0) mod channel_count
```

의미:

- `CH_Bit*Hash`는 특정 비트 하나가 아닙니다.
- 어떤 주소 비트들이 channel hash 계산에 참여할지 정하는 mask입니다.
- 그 비트들의 parity가 최종 channel bit가 됩니다.

## 3. ASYM 영역 판정

비대칭 메모리 구성인 경우, 현재 주소가 어느 영역에 속하는지 먼저 판정합니다.

현재 코드는 프로젝트별 threshold를 하드코딩하고 있습니다.

예:

- `S5AV920_8CH`
- `S5AV620_4CH`
- `S5AV920_4CH`
- `S5AV930`

이 부분은 generic LPDDR rule이라기보다 제품별 silicon rule로 보는 것이 맞습니다.

## 4. TZ config 선택

CH와 ASYM 여부에 따라 내부적으로 두 세트 중 어떤 설정값을 쓸지 결정합니다.

- index `0`
- index `1`

개념적으로는:

- `0`: 기본/대칭 쪽 설정
- `1`: ASYM 쪽 설정

이라고 보면 됩니다.

## 5. ARM address hole 제거

입력 주소를 DRAM 관점의 연속 주소처럼 보이게 바꾸는 단계입니다.

이 결과가:

- `hole_removed_addr`

입니다.

이 단계가 틀리면 뒤쪽 해석도 전부 틀어질 수 있습니다.

## 6. Interleave region 판정

현재 주소가 어느 interleave region에 속하는지 확인합니다.

대표적으로:

- `IntlvHit0`
- `IntlvHit1`
- `ExtIntlvHit0`
- `ExtIntlvHit1`

를 계산하고, 그 뒤 선택되는 값은:

- `IntlvEn`
- `IntlvSel`

입니다.

`IntlvSel` 의미:

- `3 -> 4KB`
- `2 -> 256B`
- `1 -> 128B`
- `0 -> 64B`

## 7. Interleave 비트 제거

이 단계에서:

- `Normalized_addr`

를 만듭니다.

의미:

- system/channel 분산을 위해 섞여 있던 interleave 관련 비트를 제거하고
- DRAM 내부 관점에서 더 연속적인 주소를 만드는 것

입니다.

## 8. Rank hit 판정

`Normalized_addr`가 어느 rank region에 속하는지 판정합니다.

대표 변수:

- `CsHitBase0`
- `CsHitExtBase0`
- `CsHitBase1`
- `CsHitExtBase1`

최종 결과:

- `rank = 0`
- 또는 `rank = 1`

## 9. AddrMapMode 해석

`AddrMapMode`는 매우 중요한 필드입니다.

이 값 하나가:

- bank mode
- row bit range
- column 비트 배치

를 함께 바꿉니다.

현재 코드에서는 사실상:

- `Bank16Opt4`
- `Bank16Opt1`

흐름을 중심으로 동작합니다.

## 10. Bank hash 계산

코드는 대략 아래와 같은 계산을 합니다.

```text
BANK_BitN = parity(norm_addr & (BankNHashBitEn << 7)) XOR direct_address_bit
```

그 다음:

```text
BANK = BANK_Bit3*8 + BANK_Bit2*4 + BANK_Bit1*2 + BANK_Bit0
BG = BANK // 4
BS = BANK % 4
```

### `bank hash`가 의미하는 것

이 코드에서 `bank hash`는:

- bank bit를 단순 주소 비트 슬라이스로 자르는 것이 아니라
- 여러 주소 비트를 parity로 줄인 값과
- 특정 직접 비트를 XOR해서
- 최종 bank bit를 만드는 것

입니다.

즉 최종 bank 선택은 선형 mapping이 아닙니다.

### 왜 이런 방식을 쓰는가

보통 목적은:

- 특정 bank 쏠림 완화
- bank access 분산
- 병렬성 향상

입니다.

### Bank hash 디버깅 순서

bank가 이상하면 바로 `BG`, `BS`만 보면 안 됩니다.

아래 순서로 봐야 합니다.

1. `norm_addr`가 맞는지
2. 어떤 bank mode(`Bank16Opt4` / `Bank16Opt1`)가 선택됐는지
3. `Bank*HashBitEn` 값이 무엇인지
4. 각 parity 계산값이 무엇인지
5. XOR에 들어간 직접 비트가 무엇인지
6. 최종 `BANK`, `BG`, `BS`

## 11. Rank interleave 제거

2-rank interleave가 활성화된 경우에는 rank select용으로 섞여 있던 비트를 제거해서:

- `req_addr`

를 만듭니다.

이 주소가 최종 row/column 계산에 사용됩니다.

## 12. Row 계산

`AddrMapMode`에 따라 row를 잘라내는 비트 범위가 달라집니다.

예:

- 어떤 mode는 `req_addr[27:15]`
- 어떤 mode는 `req_addr[28:15]`
- 어떤 mode는 `req_addr[29:15]`
- 어떤 mode는 `req_addr[30:15]`
- 어떤 mode는 `req_addr[31:15]`

즉 row width는 mode에 따라 달라집니다.

## 13. Column / Burst 계산

column 추출도 bank mode에 따라 달라집니다.

- `Bank16Opt4`
- `Bank16Opt1`

그 다음:

- `COL = col >> 4`
- `BUR = col & 0xF`

즉 raw column의 하위 비트는 burst offset처럼 쓰입니다.

## 주소 상태 변화 사다리

디버깅할 때는 아래처럼 주소 상태가 바뀐다고 생각하면 좋습니다.

```text
system_addr
  -> hole_removed_addr
  -> Normalized_addr
  -> req_addr
  -> row / col / bank decode
```

이 중 어느 주소를 보고 있는지 헷갈리면 디버깅이 꼬입니다.

## 실무 디버깅 순서

이 코드를 디버깅할 때는 아래 순서를 추천합니다.

## A. 설정값부터 확인

수식보다 먼저:

1. `project_code`
2. `mem_config`
3. 실제로 로딩된 Excel 값
4. ASYM 존재 여부
5. total density

를 확인합니다.

설정값이 틀리면 계산은 전부 그럴듯하게 보이더라도 결과는 완전히 틀릴 수 있습니다.

## B. Channel 경로 확인

한 주소에 대해 아래를 확인합니다.

1. `system_addr`
2. `CH_Bit2Hash`, `CH_Bit1Hash`, `CH_Bit0Hash`
3. 각 parity 값
4. 최종 `CH`
5. `ASYM_REGION`
6. `TZconfig`

## C. Interleave 경로 확인

아래를 확인합니다.

- `hole_removed_addr`
- `IntlvHit0`, `IntlvHit1`
- `ExtIntlvHit0`, `ExtIntlvHit1`
- `IntlvEn`
- `IntlvSel`
- `IntlvGranule`
- `Normalized_addr`

## D. Rank 경로 확인

아래를 확인합니다.

- `CsHitBase0`
- `CsHitExtBase0`
- `CsHitBase1`
- `CsHitExtBase1`
- `rank`

## E. Bank 경로 확인

아래를 확인합니다.

- `CfgAddrMode[rank]`
- `Bank16Opt4` 또는 `Bank16Opt1`
- `Bank3IntlvBit` ~ `Bank0IntlvBit`
- `Bank*HashBitEn`
- `BANK_Bit3` ~ `BANK_Bit0`
- `BANK`, `BG`, `BS`

## F. Row/Column 경로 확인

아래를 확인합니다.

- `req_addr`
- 선택된 row bit range
- `row`
- raw `col`
- `COL`
- `BUR`

## 추천 디버그 로그 포맷

주소 하나를 추적할 때 아래 정도를 찍으면 어느 단계에서 잘못됐는지 찾기 좋습니다.

```text
project_code=
mem_config=
system_addr=
CH=
ASYM_REGION=
TZconfig=
hole_removed_addr=
IntlvHit0/1=
ExtIntlvHit0/1=
IntlvEn=
IntlvSel=
IntlvGranule=
Normalized_addr=
CsHitBase0=
CsHitExtBase0=
CsHitBase1=
CsHitExtBase1=
rank=
AddrMode=
bank mode=
BANK_Bit3..0=
BG=
BS=
rankintlvbit=
req_addr=
row=
col=
COL=
BUR=
```

## 특히 많이 헷갈릴 수 있는 포인트

## 1. `CH`, `ASYM_REGION`, `TZconfig`는 서로 다르다

- `CH`: 최종 channel 번호
- `ASYM_REGION`: 주소가 비대칭 영역에 있는지 여부
- `TZconfig`: 어떤 설정 세트를 쓸지 정하는 내부 선택값

서로 연관은 있지만 같은 값이 아닙니다.

## 2. `BANK`와 최종 출력 `Bank`는 다르다

내부의 `BANK`는 4비트 합성 결과입니다.

출력은:

- `BankGroup`
- `Bank`

로 다시 나뉩니다.

즉:

- `BANK`는 bank+bankgroup 성격의 중간 정수
- `BG`, `BS`는 그걸 분해한 값

입니다.

## 3. `Base`와 `ExtBase`는 rank가 4개라는 뜻이 아니다

처음 보면:

- `Base0`
- `Base1`
- `ExtBase0`
- `ExtBase1`

이 네 개가 rank 4개처럼 보일 수 있습니다.

하지만 실제로는:

- rank0에 대한 base/ext-base region
- rank1에 대한 base/ext-base region

이라고 이해하는 것이 맞습니다.

## 4. `AddrMapMode`는 단순 옵션이 아니다

이 값 하나가:

- bank mode
- row bit range
- column 조합 방식

을 통째로 바꿉니다.

그래서 이 값이 잘못 들어오면 결과 전체가 틀릴 수 있습니다.

## 5. `Rank`와 `rank_num`은 다르다

헷갈리기 쉬운 부분입니다.

- `rank_num`: 해당 config에 rank가 몇 개 있는지
- `Rank`: 현재 주소가 최종적으로 선택한 rank 번호

즉 하나는 구성 정보이고, 다른 하나는 decode 결과입니다.

## 6. `CH_num`과 결과 `CH`도 다르다

- `CH_num`: 전체 channel 개수
- `CH`: 현재 주소가 선택된 channel 번호

즉 하나는 시스템 구성값이고, 하나는 decode 결과입니다.

## 테스트 없이도 제안 가능한 개선점

아래는 구조 제안입니다. 실제 반영 전에는 반드시 real config 기준 regression이 필요합니다.

## 1. 설정 로딩과 decode 로직 분리

권장 방향:

- Excel parsing은 한 모듈
- decode 계산은 한 모듈

장점:

- 읽기 쉬움
- mock/testing 쉬움
- 문제 위치 파악 쉬움

## 2. 중간 주소 상태를 명시적으로 유지

강하게 추천하는 방향:

- `system_addr`
- `hole_removed_addr`
- `Normalized_addr`
- `req_addr`

를 항상 별도 단계 값으로 유지하고 trace 가능하게 만드는 것입니다.

## 3. 프로젝트별 예외를 별도 rule 계층으로 분리

현재 ASYM threshold 같은 하드코딩 rule은 별도 `project_rules` 계층으로 옮기는 것이 좋습니다.

이유:

- silicon별 rule은 필요합니다
- 하지만 generic decode 로직과 섞여 있으면 수정 리스크가 큽니다

## 4. 내부에서는 이름 있는 모델 사용

제안:

- 외부 반환은 legacy dict 유지
- 내부는 dataclass나 명시적 모델 사용

장점:

- 의미 파악 쉬움
- 인수인계 쉬움
- index 실수 감소

## 5. Trace/debug mode 추가

강하게 추천합니다.

제안:

- `trace=True` 같은 옵션 추가
- 주소별 중간 계산값을 반환 또는 로그로 남김

이 decoder는 backend + silicon debug 용도이므로 explainability가 중요합니다.

## 6. 경계값 중심 regression 추가

실제 config가 있을 때 중요한 테스트:

- address hole 경계
- interleave region 경계
- rank 경계
- ASYM threshold 경계
- AddrMapMode별 경계
- project/config 대표 주소

랜덤 주소 대량 테스트보다 이런 경계 테스트가 훨씬 가치가 큽니다.

## LPDDR6 / 서브채널 대응 제안

## 공개 자료 기준 LPDDR6 특징 요약

공개 자료 기준으로 LPDDR6는 대략 아래 특징이 언급됩니다.

- 24-bit channel architecture
- 각 channel이 두 개의 12-bit sub-channel로 구성됨
- sub-channel당 4 bank groups 구조 언급
- normal / efficiency 관련 mode 언급
- reliability 관련 기능 강화 언급

주의:

- JEDEC 원문 전체를 직접 확인한 것은 아닙니다.
- 아래 내용은 공개 요약 자료를 바탕으로 한 설계 제안입니다.

참고한 공개 자료:

- Cadence LPDDR6 VIP 소개
  https://www.cadence.com/en_US/home/tools/system-design-and-verification/verification-ip/simulation-vip/memory-models/dram/lpddr6.html
- Synopsys LPDDR6 소개
  https://www.synopsys.com/blogs/chip-design/lpddr6-vs-lpddr5x-lpddr5-differences.html
- Synopsys LPDDR verification IP 페이지
  https://www.synopsys.com/verification/verification-ip/memory/ip-lpddr5.html
- Truechip LPDDR6 소개
  https://www.truechip.net/details/lpddr-6/701002
- KAD LPDDR6 공개 요약
  https://www.kad8.com/hardware/jedec-officially-releases-lpddr6-memory-standard/
- All About Circuits 기사
  https://www.allaboutcircuits.com/news/sk-hynix-details-low-power-ddr6-sdram-isscc-2026/

## LPDDR6가 이 decoder에 주는 구조적 영향

현재 decoder의 기본 구조는 대략 아래와 같습니다.

```text
system_addr -> channel -> rank -> bank/bg -> row/col
```

LPDDR6 대응을 하려면 최소한 아래 구조를 고려해야 합니다.

```text
system_addr -> channel -> subchannel -> rank -> bank/bg -> row/col
```

즉 sub-channel을 bank decode 안에 숨기지 말고, 별도 단계로 승격시키는 것이 좋습니다.

## 강한 제안: sub-channel 단계 명시화

추천 파이프라인:

```text
resolve_channel()
resolve_subchannel()
remove_address_hole()
resolve_interleave()
resolve_rank()
resolve_bank()
resolve_row_col()
```

이렇게 해야 하는 이유:

- channel과 sub-channel은 다른 개념입니다
- 디버깅할 때 sub-channel을 명시적으로 볼 수 있습니다
- LPDDR5에서는 sub-channel 단계를 no-op로 둘 수 있습니다

## LPDDR6 대응용 config 모델 제안

향후 이런 필드를 추가하는 것이 좋습니다.

- `dram_protocol`: `LPDDR5`, `LPDDR5X`, `LPDDR6`
- `channel_width_bits`
- `subchannel_count`
- `subchannel_width_bits`
- `bank_groups_per_subchannel`
- `banks_per_bank_group`
- `burst_access_bytes`
- `operating_mode`
- `subchannel_hash_mask` 또는 이에 준하는 project-specific selector
- `subchannel_interleave_mode`

LPDDR5 프로젝트에서는 optional로 두면 됩니다.

## LPDDR6 대응용 결과 모델 제안

내부적으로는 아래 필드를 추가할 수 있습니다.

- `SubChannel`
- `Protocol`
- `Trace`

다만 backend 호환성을 위해 기본 반환 형식은 유지하는 것이 좋습니다.

즉:

- 기존 key는 그대로 유지
- 새 필드는 trace mode나 versioned API에서만 노출

이 방향이 안전합니다.

## 안전한 LPDDR6 구조 제안

## Core engine은 단계만 안다

decode engine은 단계만 알고 있어야 합니다.

즉 core는:

- 지금 LPDDR5인지
- LPDDR6인지
- 특정 project인지

를 과하게 많이 알지 않는 것이 좋습니다.

## Protocol provider 계층 도입

권장:

- `LPDDR5Provider`
- `LPDDR6Provider`

각 provider는 아래를 정의합니다.

- 지원 AddrMapMode
- bank extraction table
- row/column extraction rule
- sub-channel behavior
- protocol-specific restriction

## Project rule 계층은 별도 유지

project별 rule은 protocol rule과 분리합니다.

예:

- ASYM threshold
- project-specific hash mask
- custom address hole map
- custom threshold

이렇게 분리해야:

- LPDDR6 generic logic
- 제품별 예외

가 섞이지 않습니다.

## LPDDR6 도입 시 권장 단계

### 1단계

LPDDR5 decode 수학은 건드리지 않습니다.

먼저:

- stage 분리
- trace 확보
- sub-channel stage 틀만 추가

만 합니다.

### 2단계

LPDDR6 config schema를 추가합니다.

아직 LPDDR5 경로와 섞지 않습니다.

### 3단계

LPDDR6 provider를 별도로 구현합니다.

### 4단계

protocol regression과 project regression을 분리해서 검증합니다.

이게 중요한 이유:

- LPDDR6 지원 때문에 LPDDR5가 조용히 깨지면 안 되기 때문입니다.

## 하지 말아야 할 것

이 코드베이스에서는 아래 접근이 위험합니다.

- 모든 project rule을 너무 빨리 일반화하기
- sub-channel 처리를 row/column table 안에 숨기기
- 중간 상태 변수를 줄이겠다고 한 줄 수식으로 합치기
- backend 반환 형식을 바꾸기
- JEDEC 일반 개념만 보고 controller-specific hash를 무시하기

## 실무 유지보수 관점 요약

이 코드를 회사에서 디버깅/유지보수할 때 가장 안전한 사고방식은 아래입니다.

## 1. 한 번에 보지 말고 단계별로 본다

문제는 보통 아래 중 하나입니다.

- 설정값 로딩이 틀림
- channel hash가 틀림
- ASYM region 선택이 틀림
- address hole 제거가 틀림
- interleave 판정이 틀림
- rank 판정이 틀림
- bank hash가 틀림
- row/column extraction이 틀림

## 2. Row/Column부터 보면 안 된다

항상 아래 순서로 확인합니다.

1. config
2. channel
3. hole removal
4. interleave
5. rank
6. bank
7. row/column

## 3. Bank hash는 "어디서 비트를 잘랐는가"가 아니다

bank hash는:

- 어떤 비트를 선택했는가
- parity가 어떻게 나왔는가
- direct bit와 XOR가 어떻게 됐는가

까지 포함해서 봐야 합니다.

## 4. 기준 구현은 여전히 `decoder.py`

실제 config 기준 regression이 끝나기 전까지는:

- `decoder.py`가 truth source
- 리팩토링 경로는 읽기 쉽고 확장 가능한 초안

으로 보는 것이 안전합니다.

## 최종 결론

앞으로 LPDDR6 + sub-channel 대응이 필요하다면, 정답은 대규모 재작성보다 **단계 분리 + trace 강화 + protocol/project rule 분리**입니다.

가장 안전한 방향은 아래입니다.

1. LPDDR5 기존 동작은 절대 바꾸지 않는다
2. stage를 명시적으로 드러낸다
3. trace/debug visibility를 높인다
4. sub-channel을 first-class stage로 추가한다
5. protocol rule과 project rule을 분리한다
6. 실제 config 기준 regression 후에만 backend cutover 한다

이 방향이 유지보수성과 실리콘 안정성을 동시에 지키는 쪽입니다.
