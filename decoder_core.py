from .bitops import cut_bits, find_zero_lsb, inv_bits, parity
from .config_parser import build_register_state, load_asym_config, load_primary_config
from .models import AddressState, DecodeResult
from .project_rules import resolve_asym_region


def remove_duplicates(input_list):
    input_list = [x.strip() for x in input_list]
    return list(set(input_list))


def get_memory_configuration_list(info, df):
    chasym = info.CHASYM
    ch_num = info.CH_num

    config_list = []
    for i, configuration in enumerate(df.loc["Configuration"], start=1):
        if not chasym:
            if df[i]["rank_num"] == 1:
                config = f"{i} : {configuration} || RANK0 : {int(df[i]['rank0_density'])}Gb"
            elif df[i]["rank_num"] == 2:
                config = (
                    f"{i} : {configuration} || RANK0 : {int(df[i]['rank0_density'])}Gb  "
                    f"RANK1 : {int(df[i]['rank1_density'])}Gb"
                )
        elif df[i]["ASYM_rank_num"] == 0:
            if df[i]["rank_num"] == 1:
                config = f"{i} : {configuration} || RANK0 : {int(df[i]['rank0_density'])}Gb"
            elif df[i]["rank_num"] == 2:
                config = (
                    f"{i} : {configuration} || RANK0 : {int(df[i]['rank0_density'])}Gb  "
                    f"RANK1 : {int(df[i]['rank1_density'])}Gb"
                )
        else:
            if ch_num == 8:
                ch_left, ch_right = "CH0123", "CH4567"
            elif ch_num == 4:
                ch_left, ch_right = "CH01", "CH23"

            if df[i]["rank_num"] == 1:
                if df[i]["ASYM_rank_num"] == 1:
                    config = (
                        f"{i} : {configuration} || {ch_left} RANK0 : {int(df[i]['rank0_density'])}Gb || "
                        f"{ch_right} RANK0 : {int(df[i]['ASYM_rank0_density'])}Gb"
                    )
                elif df[i]["ASYM_rank_num"] == 2:
                    config = (
                        f"{i} : {configuration} || {ch_left} RANK0 : {int(df[i]['rank0_density'])}Gb || "
                        f"{ch_right} RANK0 : {int(df[i]['ASYM_rank0_density'])}Gb  "
                        f"RANK1 : {int(df[i]['ASYM_rank1_density'])}Gb"
                    )
            elif df[i]["rank_num"] == 2:
                if df[i]["ASYM_rank_num"] == 1:
                    config = (
                        f"{i} : {configuration} || {ch_left} RANK0 : {int(df[i]['rank0_density'])}Gb  "
                        f"RANK1 : {int(df[i]['rank1_density'])}Gb || "
                        f"{ch_right} RANK0 : {int(df[i]['ASYM_rank0_density'])}Gb"
                    )
                elif df[i]["ASYM_rank_num"] == 2:
                    config = (
                        f"{i} : {configuration} || {ch_left} RANK0 : {int(df[i]['rank0_density'])}Gb  "
                        f"RANK1 : {int(df[i]['rank1_density'])}Gb || {ch_right} RANK0 : "
                        f"{int(df[i]['ASYM_rank0_density'])}Gb  RANK1 : {int(df[i]['ASYM_rank1_density'])}Gb"
                    )

        config_list.append(config)

    print(config_list)
    return config_list


# -----------------------------------------------------------------------------
# 내부 헬퍼
# -----------------------------------------------------------------------------


def _build_hash_config(info):
    """채널/뱅크 해시 계산에 필요한 마스크를 정수로 변환한다."""
    return {
        "ch_num": info.CH_num,
        "ch_bit2_hash": int(info.CH_Bit2Hash, 16),
        "ch_bit1_hash": int(info.CH_Bit1Hash, 16),
        "ch_bit0_hash": int(info.CH_Bit0Hash, 16),
        "bank3_hash_bit_en": int(info.Bank3HashBitEn, 16),
        "bank2_hash_bit_en": int(info.Bank2HashBitEn, 16),
        "bank1_hash_bit_en": int(info.Bank1HashBitEn, 16),
        "bank0_hash_bit_en": int(info.Bank0HashBitEn, 16),
    }


def _compute_total_density(registers, ch_num):
    if registers["rank_num"][1] == 0:
        return (registers["rank0_density"][0] + registers["rank1_density"][0]) * ch_num / 8
    return (
        registers["rank0_density"][0]
        + registers["rank1_density"][0]
        + registers["rank0_density"][1]
        + registers["rank1_density"][1]
    ) * ch_num / 2 / 8


def _resolve_channel(system_addr, hash_cfg, asym_region):
    """
    channel은 주소 비트 해시(parity) 기반으로 계산한다.
    rank처럼 영역 hit로 고르는 게 아니라, 여러 비트를 XOR/parity 해서 분산 선택한다.
    """
    ch_bit2 = parity(system_addr & hash_cfg["ch_bit2_hash"])
    ch_bit1 = parity(system_addr & hash_cfg["ch_bit1_hash"])
    ch_bit0 = parity(system_addr & hash_cfg["ch_bit0_hash"])
    return int((ch_bit2 * 4 + ch_bit1 * 2 + ch_bit0) % (hash_cfg["ch_num"] / (asym_region + 1)))


def _resolve_subchannel(system_addr, hash_cfg):
    """
    LPDDR6용 subchannel resolve 단계.
    CHConfig의 `SubChHashBitEn`가 비어 있지 않으면 LP6 프로젝트로 보고,
    channel hash와 같은 계열의 parity 해시 방식으로 subchannel(0/1)을 계산한다.
    값이 없으면 기존 LPDDR5 경로로 간주해 None을 반환한다.
    """
    if hash_cfg["subch_hash_bit_en"] == 0:
        return None
    return parity(system_addr & hash_cfg["subch_hash_bit_en"])


def _select_tzconfig(registers, ch, ch_num):
    """ASYM 구성일 때 채널 위치에 따라 좌/우 TZ config(0/1)를 고른다."""
    if registers["rank_num"][1] != 0 and ch >= (ch_num / 2):
        return 1
    return 0


def _extract_tzconfig_view(registers, tzconfig):
    """
    선택된 tzconfig에서 실제 decode에 필요한 register-like 값을 꺼낸다.
    이후 rank/bank/row/col 계산은 이 view 기준으로만 동작한다.
    """
    return {
        "cfg_base_ad_38_12": [
            cut_bits(registers["BaseAddr0"][tzconfig], 30, 4),
            cut_bits(registers["BaseAddr1"][tzconfig], 30, 4),
        ],
        "cfg_rank_en": [
            cut_bits(registers["BaseAddr0"][tzconfig], 0, 0),
            cut_bits(registers["BaseAddr1"][tzconfig], 0, 0),
        ],
        "cfg_base_mask_38_12": [
            cut_bits(registers["BaseMask0"][tzconfig], 30, 4),
            cut_bits(registers["BaseMask1"][tzconfig], 30, 4),
        ],
        "cfg_ext_base_ad_38_12": [
            cut_bits(registers["ExtBaseAddr0"][tzconfig], 30, 4),
            cut_bits(registers["ExtBaseAddr1"][tzconfig], 30, 4),
        ],
        "cfg_ext_rank_en": [
            cut_bits(registers["ExtBaseAddr0"][tzconfig], 0, 0),
            cut_bits(registers["ExtBaseAddr1"][tzconfig], 0, 0),
        ],
        "cfg_ext_base_mask_38_12": [
            cut_bits(registers["ExtBaseMask0"][tzconfig], 30, 4),
            cut_bits(registers["ExtBaseMask1"][tzconfig], 30, 4),
        ],
        "cfg_addr_mode": [
            cut_bits(registers["AddrMapMode"][tzconfig], 5, 0),
            cut_bits(registers["AddrMapMode"][tzconfig], 21, 16),
        ],
        "cfg_reduce_page_size_en": cut_bits(registers["BankAddrMode"][tzconfig], 0, 0),
        "cfg_intlv_base_ad_38_29": [
            cut_bits(registers["IntlvBaseAddr0"][tzconfig], 18, 9),
            cut_bits(registers["IntlvBaseAddr1"][tzconfig], 18, 9),
        ],
        "cfg_intlv_en": [
            cut_bits(registers["IntlvBaseAddr0"][tzconfig], 1, 0),
            cut_bits(registers["IntlvBaseAddr1"][tzconfig], 1, 0),
        ],
        "cfg_intlv_base_mask_38_29": [
            cut_bits(registers["IntlvBaseMask0"][tzconfig], 18, 9),
            cut_bits(registers["IntlvBaseMask1"][tzconfig], 18, 9),
        ],
        "cfg_intlv_select": [
            cut_bits(registers["IntlvBaseMask0"][tzconfig], 1, 0),
            cut_bits(registers["IntlvBaseMask1"][tzconfig], 1, 0),
        ],
        "cfg_rank_interleave_en": cut_bits(registers["TzSpare"][tzconfig], 0, 0),
        "cfg_ext_intlv_base_ad_38_29": [
            cut_bits(registers["ExtIntlvBaseAddr0"][tzconfig], 18, 9),
            cut_bits(registers["ExtIntlvBaseAddr1"][tzconfig], 18, 9),
        ],
        "cfg_ext_intlv_en": [
            cut_bits(registers["ExtIntlvBaseAddr0"][tzconfig], 1, 0),
            cut_bits(registers["ExtIntlvBaseAddr1"][tzconfig], 1, 0),
        ],
        "cfg_ext_intlv_base_mask_38_29": [
            cut_bits(registers["ExtIntlvBaseMask0"][tzconfig], 18, 9),
            cut_bits(registers["ExtIntlvBaseMask1"][tzconfig], 18, 9),
        ],
        "cfg_ext_intlv_select": [
            cut_bits(registers["ExtIntlvBaseMask0"][tzconfig], 1, 0),
            cut_bits(registers["ExtIntlvBaseMask1"][tzconfig], 1, 0),
        ],
    }


def _remove_address_hole(system_addr):
    """
    ARM address map hole을 제거해 연속 공간처럼 다루기 위한 주소를 만든다.
    이후 interleave 해석은 이 hole-removed 주소 기준으로 진행한다.
    """
    if (system_addr <= 0xFFFFFFFF) and (system_addr >= 0x80000000):
        return system_addr - 0x80000000
    if (system_addr <= 0xFFFFFFFFF) and (system_addr >= 0x880000000):
        return system_addr - 0x800000000
    if (system_addr >= 0x8800000000) and (system_addr <= 0x8FFFFFFFFF):
        return system_addr - 0x8000000000
    raise ValueError(
        "[ERROR] Input Address {0} does not follow the ARM address map base or "
        "mpace_address is more than 64GB region".format(hex(system_addr))
    )


def _resolve_interleave_view(hole_removed_addr, tz):
    """
    interleave region hit 여부와 granule/enable 값을 계산한다.
    주의: 이 단계는 system_addr가 아니라 hole_removed_addr 기준이다.
    """
    cfg_intlv_base_ad_38_29 = tz["cfg_intlv_base_ad_38_29"]
    cfg_intlv_en = tz["cfg_intlv_en"]
    cfg_intlv_base_mask_38_29 = tz["cfg_intlv_base_mask_38_29"]
    cfg_intlv_select = tz["cfg_intlv_select"]
    cfg_ext_intlv_base_ad_38_29 = tz["cfg_ext_intlv_base_ad_38_29"]
    cfg_ext_intlv_en = tz["cfg_ext_intlv_en"]
    cfg_ext_intlv_base_mask_38_29 = tz["cfg_ext_intlv_base_mask_38_29"]
    cfg_ext_intlv_select = tz["cfg_ext_intlv_select"]

    intlv_hit0 = ((cfg_intlv_select[0] != 0) | (cfg_intlv_en != 0)) & (
        (cfg_intlv_base_ad_38_29[0] & inv_bits(cfg_intlv_base_mask_38_29[0], 38 - 29 + 1))
        == (cut_bits(hole_removed_addr, 38, 29) & inv_bits(cfg_intlv_base_mask_38_29[0], 38 - 29 + 1))
    )
    intlv_hit1 = ((cfg_intlv_select[1] != 0) | (cfg_intlv_en != 0)) & (
        (cfg_intlv_base_ad_38_29[1] & inv_bits(cfg_intlv_base_mask_38_29[1], 38 - 29 + 1))
        == (cut_bits(hole_removed_addr, 38, 29) & inv_bits(cfg_intlv_base_mask_38_29[1], 38 - 29 + 1))
    )
    ext_intlv_hit0 = ((cfg_ext_intlv_select[0] != 0) | (cfg_ext_intlv_en != 0)) & (
        (cfg_ext_intlv_base_ad_38_29[0] & inv_bits(cfg_ext_intlv_base_mask_38_29[0], 38 - 29 + 1))
        == (cut_bits(hole_removed_addr, 38, 29) & inv_bits(cfg_ext_intlv_base_mask_38_29[0], 38 - 29 + 1))
    )
    ext_intlv_hit1 = ((cfg_ext_intlv_select[1] != 0) | (cfg_ext_intlv_en != 0)) & (
        (cfg_ext_intlv_base_ad_38_29[1] & inv_bits(cfg_ext_intlv_base_mask_38_29[1], 38 - 29 + 1))
        == (cut_bits(hole_removed_addr, 38, 29) & inv_bits(cfg_ext_intlv_base_mask_38_29[1], 38 - 29 + 1))
    )

    if intlv_hit0 == 1:
        intlv_en = cfg_intlv_en[0]
        intlv_sel = cfg_intlv_select[0]
    elif intlv_hit1 == 1:
        intlv_en = cfg_intlv_en[1]
        intlv_sel = cfg_intlv_select[1]
    elif ext_intlv_hit0 == 1:
        intlv_en = cfg_ext_intlv_en[0]
        intlv_sel = cfg_ext_intlv_select[0]
    elif ext_intlv_hit1 == 1:
        intlv_en = cfg_ext_intlv_en[1]
        intlv_sel = cfg_ext_intlv_select[1]
    else:
        raise ValueError(
            "[ERROR] Hole removed Addr {0} does not belong to any of the set intlvregion.".format(
                hex(hole_removed_addr)
            )
        )

    if intlv_sel == 3:
        intlv_granule = 12
    elif intlv_sel == 2:
        intlv_granule = 8
    elif intlv_sel == 1:
        intlv_granule = 7
    else:
        intlv_granule = 6

    return {
        "intlv_en": intlv_en,
        "intlv_sel": intlv_sel,
        "intlv_granule": intlv_granule,
    }


def _normalize_addr(hole_removed_addr, intlv):
    """interleave selection 비트를 제거한 normalized address를 만든다."""
    return ((hole_removed_addr >> (intlv["intlv_granule"] + intlv["intlv_en"])) << intlv["intlv_granule"]) + (
        cut_bits(hole_removed_addr, intlv["intlv_granule"] - 1, 0)
    )


def _resolve_rank(norm_addr, tz):
    """
    rank는 해시가 아니라 region hit(base/mask) 판정으로 결정한다.
    따라서 channel/bank 해시와 원리가 다르다.
    """
    cfg_base_ad_38_12 = tz["cfg_base_ad_38_12"]
    cfg_rank_en = tz["cfg_rank_en"]
    cfg_base_mask_38_12 = tz["cfg_base_mask_38_12"]
    cfg_ext_base_ad_38_12 = tz["cfg_ext_base_ad_38_12"]
    cfg_ext_rank_en = tz["cfg_ext_rank_en"]
    cfg_ext_base_mask_38_12 = tz["cfg_ext_base_mask_38_12"]
    cfg_addr_mode = tz["cfg_addr_mode"]

    cs_hit_base0 = cfg_rank_en[0] & (
        (cfg_base_ad_38_12[0] & inv_bits(cfg_base_mask_38_12[0], 38 - 12 + 1))
        == (cut_bits(norm_addr, 38, 12) & inv_bits(cfg_base_mask_38_12[0], 38 - 12 + 1))
    )
    cs_hit_ext_base0 = cfg_ext_rank_en[0] & (
        (cfg_ext_base_ad_38_12[0] & inv_bits(cfg_ext_base_mask_38_12[0], 38 - 12 + 1))
        == (cut_bits(norm_addr, 38, 12) & inv_bits(cfg_ext_base_mask_38_12[0], 38 - 12 + 1))
    )
    cs_hit_base1 = cfg_rank_en[1] & (
        (cfg_base_ad_38_12[1] & inv_bits(cfg_base_mask_38_12[1], 38 - 12 + 1))
        == (cut_bits(norm_addr, 38, 12) & inv_bits(cfg_base_mask_38_12[1], 38 - 12 + 1))
    )
    cs_hit_ext_base1 = cfg_ext_rank_en[1] & (
        (cfg_ext_base_ad_38_12[1] & inv_bits(cfg_ext_base_mask_38_12[1], 38 - 12 + 1))
        == (cut_bits(norm_addr, 38, 12) & inv_bits(cfg_ext_base_mask_38_12[1], 38 - 12 + 1))
    )

    two_rank = cfg_rank_en[0] & cfg_rank_en[1]
    cs_hit0 = cs_hit_base0 | cs_hit_ext_base0
    cs_hit1 = cs_hit_base1 | cs_hit_ext_base1

    if cs_hit0 == 1:
        rank = 0
    elif cs_hit1 == 1:
        rank = 1
    else:
        raise ValueError(
            "[ERROR] Normalized Addr {0} does not belong to any of the set Rank Region".format(
                hex(norm_addr)
            )
        )

    return {
        "rank": rank,
        "two_rank": two_rank,
        "cs_hit_base0": cs_hit_base0,
        "cs_hit_ext_base0": cs_hit_ext_base0,
        "cs_hit_base1": cs_hit_base1,
        "cs_hit_ext_base1": cs_hit_ext_base1,
        "cfg_addr_mode": cfg_addr_mode,
    }


def _resolve_bank(norm_addr, rank_info, hash_cfg):
    """
    bank는 channel과 마찬가지로 해시(parity/XOR) 기반이다.
    다만 어떤 비트를 쓸지는 rank의 addr_mode에 따라 달라진다.
    """
    rank = rank_info["rank"]
    cfg_addr_mode = rank_info["cfg_addr_mode"]

    bank16opt4 = 0
    bank16opt1 = 0
    if cut_bits(cfg_addr_mode[rank], 5, 3) == 0b110:
        bank16opt4 = 1
    elif cut_bits(cfg_addr_mode[rank], 5, 3) == 0b011:
        bank16opt1 = 1
    else:
        raise ValueError("AddrMode{0} {1} is not supported".format(rank, cfg_addr_mode[rank]))

    if bank16opt4 == 1:
        bank3_intlv_bit = 8
        bank2_intlv_bit = 12
        bank1_intlv_bit = 14
        bank0_intlv_bit = 13
    else:
        bank3_intlv_bit = 6
        bank2_intlv_bit = 11
        bank1_intlv_bit = 13
        bank0_intlv_bit = 12

    bank_bit3 = parity(norm_addr & (hash_cfg["bank3_hash_bit_en"] << 7)) ^ cut_bits(norm_addr, bank3_intlv_bit, bank3_intlv_bit)
    bank_bit2 = parity(norm_addr & (hash_cfg["bank2_hash_bit_en"] << 7)) ^ cut_bits(norm_addr, bank2_intlv_bit, bank2_intlv_bit)
    bank_bit1 = parity(norm_addr & (hash_cfg["bank1_hash_bit_en"] << 7)) ^ cut_bits(norm_addr, bank1_intlv_bit, bank1_intlv_bit)
    bank_bit0 = parity(norm_addr & (hash_cfg["bank0_hash_bit_en"] << 7)) ^ cut_bits(norm_addr, bank0_intlv_bit, bank0_intlv_bit)

    bank = bank_bit3 * 8 + bank_bit2 * 4 + bank_bit1 * 2 + bank_bit0
    return {
        "bank": bank,
        "bg": bank // 4,
        "bs": bank % 4,
        "bank16opt4": bank16opt4,
        "bank16opt1": bank16opt1,
    }


def _resolve_req_addr(norm_addr, rank_info, tz):
    """
    row/col은 req_addr 기준으로 계산한다.
    따라서 rank interleave가 켜져 있으면, 여기서 rank select 비트를 제거한 주소를 만들어야 한다.
    """
    cs_hit_base0 = rank_info["cs_hit_base0"]
    cs_hit_ext_base0 = rank_info["cs_hit_ext_base0"]
    cs_hit_base1 = rank_info["cs_hit_base1"]
    cs_hit_ext_base1 = rank_info["cs_hit_ext_base1"]
    two_rank = rank_info["two_rank"]
    cfg_base_mask_38_12 = tz["cfg_base_mask_38_12"]
    cfg_ext_base_mask_38_12 = tz["cfg_ext_base_mask_38_12"]
    cfg_rank_interleave_en = tz["cfg_rank_interleave_en"]

    rankintlvbit = 0
    if cs_hit_base0 == 1:
        rankintlvbit = find_zero_lsb(cfg_base_mask_38_12[0]) + 12
    elif cs_hit_ext_base0 == 1:
        rankintlvbit = find_zero_lsb(cfg_ext_base_mask_38_12[0]) + 12
    elif cs_hit_base1 == 1:
        rankintlvbit = find_zero_lsb(cfg_base_mask_38_12[1]) + 12
    elif cs_hit_ext_base1 == 1:
        rankintlvbit = find_zero_lsb(cfg_ext_base_mask_38_12[1]) + 12

    if (two_rank == 1) & cfg_rank_interleave_en:
        req_addr = (cut_bits(norm_addr, 32, rankintlvbit + 1) << rankintlvbit) + cut_bits(norm_addr, rankintlvbit - 1, 0)
    else:
        req_addr = norm_addr

    return {"req_addr": req_addr, "rankintlvbit": rankintlvbit}


def _resolve_row(req_addr, addr_mode):
    """row는 req_addr와 addr_mode 조합으로 잘라낸다."""
    if addr_mode in (0b010000, 0b011000, 0b110000):
        return cut_bits(req_addr, 27, 15)
    if addr_mode in (0b010001, 0b011001, 0b110001):
        return cut_bits(req_addr, 28, 15)
    if addr_mode in (0b010010, 0b011010, 0b110010):
        return cut_bits(req_addr, 29, 15)
    if addr_mode in (0b010011, 0b011011, 0b110011):
        return cut_bits(req_addr, 30, 15)
    if addr_mode in (0b010100, 0b011100, 0b110100):
        return cut_bits(req_addr, 31, 15)
    raise ValueError("AddrMode {0} is not supported".format(addr_mode))


def _resolve_col(req_addr, bank_info, cfg_reduce_page_size_en):
    """column과 burst는 req_addr 기준으로 계산한다."""
    if bank_info["bank16opt4"] == 1:
        col = (cut_bits(req_addr, 11, 9) << 7) + cut_bits(req_addr, 7, 1)
    elif bank_info["bank16opt1"] == 1:
        col = (cut_bits(req_addr, 14, 14) << 9) + (cut_bits(req_addr, 10, 7) << 5) + cut_bits(req_addr, 5, 1)
    else:
        col = cfg_reduce_page_size_en
    return col >> 4, hex(col & 0xF)


# -----------------------------------------------------------------------------
# 메인 decode 파이프라인
# -----------------------------------------------------------------------------


def decode_addresses(context, system_addrs):
    """
    legacy decode 순서를 유지하면서도, 내부 단계를 읽기 쉬운 파이프라인으로 나눈다.

    순서:
    1) resolve_channel(system_addr)
    2) resolve_subchannel(system_addr)        # LPDDR5 경로에서는 None
    3) select_tzconfig(ch, asym_region)
    4) remove_address_hole(system_addr)
    5) resolve_interleave(hole_removed_addr)
    6) normalize_addr(hole_removed_addr)
    7) resolve_rank(norm_addr)
    8) resolve_bank(norm_addr)
    9) resolve_req_addr(norm_addr)
    10) resolve_row(req_addr)
    11) resolve_col(req_addr)
    12) build_legacy_result(...)
    """
    system_addrs = remove_duplicates(system_addrs)
    excel_data = context.excel_data
    config = context.config
    info = context.info
    df = context.project_df

    excel_data["ch_info"] = info.to_dict()
    print("Selected Project = {0}".format(context.project_code))
    excel_data["tz"] = df[config].tolist()

    hash_cfg = _build_hash_config(info)
    registers = build_register_state()
    load_primary_config(df, config, registers)
    load_asym_config(df, config, registers)
    total_density = _compute_total_density(registers, hash_cfg["ch_num"])

    result = []
    for system_addr_text in system_addrs:
        address_state = AddressState(system_addr=int(system_addr_text, 16))

        # 1) channel / subchannel / asym / tzconfig 선택은 system_addr 기준
        asym_region = 0
        if registers["rank_num"][1] != 0:
            asym_region = resolve_asym_region(context.project_code, total_density, address_state.system_addr)
        ch = _resolve_channel(address_state.system_addr, hash_cfg, asym_region)
        subch = _resolve_subchannel(address_state.system_addr, hash_cfg)
        tzconfig = _select_tzconfig(registers, ch, hash_cfg["ch_num"])
        tz = _extract_tzconfig_view(registers, tzconfig)

        # 2) ARM hole 제거 후 interleave 해석용 주소 생성
        hole_removed_addr = _remove_address_hole(address_state.system_addr)
        address_state = AddressState(
            system_addr=address_state.system_addr,
            hole_removed_addr=hole_removed_addr,
        )

        # 3) interleave 제거 -> normalized address
        intlv = _resolve_interleave_view(address_state.hole_removed_addr, tz)
        norm_addr = _normalize_addr(address_state.hole_removed_addr, intlv)
        address_state = AddressState(
            system_addr=address_state.system_addr,
            hole_removed_addr=address_state.hole_removed_addr,
            norm_addr=norm_addr,
        )

        # 4) rank / bank는 norm_addr 기준
        rank_info = _resolve_rank(address_state.norm_addr, tz)
        bank_info = _resolve_bank(address_state.norm_addr, rank_info, hash_cfg)

        # 5) row / col 계산 전에 req_addr 정리
        req_info = _resolve_req_addr(address_state.norm_addr, rank_info, tz)
        address_state = AddressState(
            system_addr=address_state.system_addr,
            hole_removed_addr=address_state.hole_removed_addr,
            norm_addr=address_state.norm_addr,
            req_addr=req_info["req_addr"],
        )

        rank = rank_info["rank"]
        row = _resolve_row(address_state.req_addr, rank_info["cfg_addr_mode"][rank])
        col_value, bur = _resolve_col(address_state.req_addr, bank_info, tz["cfg_reduce_page_size_en"])

        # legacy 출력 shape는 그대로 유지한다.
        result.append(
            DecodeResult(
                Physical_addr=hex(address_state.system_addr),
                Normalized_addr=hex(address_state.norm_addr),
                CH=ch,
                Rank=rank % 2,
                BankGroup=bank_info["bg"],
                Bank=bank_info["bs"],
                Row=row,
                Col=col_value,
                Bur=bur,
            ).to_legacy_dict()
        )

    print(result)
    return result, excel_data
cel_data
