from .bitops import cut_bits, find_zero_lsb, inv_bits, parity
from .config_parser import build_register_state, load_asym_config, load_primary_config
from .models import DecodeResult
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


def decode_addresses(context, system_addrs):
    system_addrs = remove_duplicates(system_addrs)
    excel_data = context.excel_data
    config = context.config
    info = context.info
    df = context.project_df

    excel_data["ch_info"] = info.to_dict()
    print("Selected Project = {0}".format(context.project_code))
    excel_data["tz"] = df[config].tolist()

    ch_num = info.CH_num

    ch_bit2_hash = int(info.CH_Bit2Hash, 16)
    ch_bit1_hash = int(info.CH_Bit1Hash, 16)
    ch_bit0_hash = int(info.CH_Bit0Hash, 16)
    bank3_hash_bit_en = int(info.Bank3HashBitEn, 16)
    bank2_hash_bit_en = int(info.Bank2HashBitEn, 16)
    bank1_hash_bit_en = int(info.Bank1HashBitEn, 16)
    bank0_hash_bit_en = int(info.Bank0HashBitEn, 16)

    registers = build_register_state()
    load_primary_config(df, config, registers)
    load_asym_config(df, config, registers)

    if registers["rank_num"][1] == 0:
        total_density = (
            registers["rank0_density"][0] + registers["rank1_density"][0]
        ) * ch_num / 8
    else:
        total_density = (
            registers["rank0_density"][0]
            + registers["rank1_density"][0]
            + registers["rank0_density"][1]
            + registers["rank1_density"][1]
        ) * ch_num / 2 / 8

    result = []
    for system_addr_text in system_addrs:
        system_addr = int(system_addr_text, 16)
        ch_bit2 = parity(system_addr & ch_bit2_hash)
        ch_bit1 = parity(system_addr & ch_bit1_hash)
        ch_bit0 = parity(system_addr & ch_bit0_hash)

        asym_region = 0
        if registers["rank_num"][1] != 0:
            asym_region = resolve_asym_region(context.project_code, total_density, system_addr)

        ch = int((ch_bit2 * 4 + ch_bit1 * 2 + ch_bit0 * 1) % (ch_num / (asym_region + 1)))

        if registers["rank_num"][1] != 0:
            if ch >= (ch_num / 2):
                tzconfig = 1
            else:
                tzconfig = 0
        else:
            tzconfig = 0

        cfg_base_ad_38_12 = [
            cut_bits(registers["BaseAddr0"][tzconfig], 30, 4),
            cut_bits(registers["BaseAddr1"][tzconfig], 30, 4),
        ]
        cfg_rank_en = [
            cut_bits(registers["BaseAddr0"][tzconfig], 0, 0),
            cut_bits(registers["BaseAddr1"][tzconfig], 0, 0),
        ]
        cfg_base_mask_38_12 = [
            cut_bits(registers["BaseMask0"][tzconfig], 30, 4),
            cut_bits(registers["BaseMask1"][tzconfig], 30, 4),
        ]
        cfg_ext_base_ad_38_12 = [
            cut_bits(registers["ExtBaseAddr0"][tzconfig], 30, 4),
            cut_bits(registers["ExtBaseAddr1"][tzconfig], 30, 4),
        ]
        cfg_ext_rank_en = [
            cut_bits(registers["ExtBaseAddr0"][tzconfig], 0, 0),
            cut_bits(registers["ExtBaseAddr1"][tzconfig], 0, 0),
        ]
        cfg_ext_base_mask_38_12 = [
            cut_bits(registers["ExtBaseMask0"][tzconfig], 30, 4),
            cut_bits(registers["ExtBaseMask1"][tzconfig], 30, 4),
        ]
        cfg_addr_mode = [
            cut_bits(registers["AddrMapMode"][tzconfig], 5, 0),
            cut_bits(registers["AddrMapMode"][tzconfig], 21, 16),
        ]
        cfg_reduce_page_size_en = cut_bits(registers["BankAddrMode"][tzconfig], 0, 0)
        cfg_intlv_base_ad_38_29 = [
            cut_bits(registers["IntlvBaseAddr0"][tzconfig], 18, 9),
            cut_bits(registers["IntlvBaseAddr1"][tzconfig], 18, 9),
        ]
        cfg_intlv_en = [
            cut_bits(registers["IntlvBaseAddr0"][tzconfig], 1, 0),
            cut_bits(registers["IntlvBaseAddr1"][tzconfig], 1, 0),
        ]
        cfg_intlv_base_mask_38_29 = [
            cut_bits(registers["IntlvBaseMask0"][tzconfig], 18, 9),
            cut_bits(registers["IntlvBaseMask1"][tzconfig], 18, 9),
        ]
        cfg_intlv_select = [
            cut_bits(registers["IntlvBaseMask0"][tzconfig], 1, 0),
            cut_bits(registers["IntlvBaseMask1"][tzconfig], 1, 0),
        ]
        cfg_rank_interleave_en = cut_bits(registers["TzSpare"][tzconfig], 0, 0)
        cfg_ext_intlv_base_ad_38_29 = [
            cut_bits(registers["ExtIntlvBaseAddr0"][tzconfig], 18, 9),
            cut_bits(registers["ExtIntlvBaseAddr1"][tzconfig], 18, 9),
        ]
        cfg_ext_intlv_en = [
            cut_bits(registers["ExtIntlvBaseAddr0"][tzconfig], 1, 0),
            cut_bits(registers["ExtIntlvBaseAddr1"][tzconfig], 1, 0),
        ]
        cfg_ext_intlv_base_mask_38_29 = [
            cut_bits(registers["ExtIntlvBaseMask0"][tzconfig], 18, 9),
            cut_bits(registers["ExtIntlvBaseMask1"][tzconfig], 18, 9),
        ]
        cfg_ext_intlv_select = [
            cut_bits(registers["ExtIntlvBaseMask0"][tzconfig], 1, 0),
            cut_bits(registers["ExtIntlvBaseMask1"][tzconfig], 1, 0),
        ]

        mpace_aaddr = system_addr

        if (mpace_aaddr <= 0xFFFFFFFF) and (mpace_aaddr >= 0x80000000):
            hole_removed_addr = mpace_aaddr - 0x80000000
        elif (mpace_aaddr <= 0xFFFFFFFFF) and (mpace_aaddr >= 0x880000000):
            hole_removed_addr = mpace_aaddr - 0x800000000
        elif (mpace_aaddr >= 0x8800000000) and (mpace_aaddr <= 0x8FFFFFFFFF):
            hole_removed_addr = mpace_aaddr - 0x8000000000
        else:
            raise ValueError(
                "[ERROR] Input Address {0} does not follow the ARM address map base or "
                "mpace_address is more than 64GB region".format(hex(mpace_aaddr))
            )

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
        elif intlv_sel == 0:
            intlv_granule = 6

        norm_addr = ((hole_removed_addr >> (intlv_granule + intlv_en)) << intlv_granule) + (
            cut_bits(hole_removed_addr, intlv_granule - 1, 0)
        )

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
        elif bank16opt1 == 1:
            bank3_intlv_bit = 6
            bank2_intlv_bit = 11
            bank1_intlv_bit = 13
            bank0_intlv_bit = 12

        bank_bit3 = parity(norm_addr & (bank3_hash_bit_en << 7)) ^ cut_bits(norm_addr, bank3_intlv_bit, bank3_intlv_bit)
        bank_bit2 = parity(norm_addr & (bank2_hash_bit_en << 7)) ^ cut_bits(norm_addr, bank2_intlv_bit, bank2_intlv_bit)
        bank_bit1 = parity(norm_addr & (bank1_hash_bit_en << 7)) ^ cut_bits(norm_addr, bank1_intlv_bit, bank1_intlv_bit)
        bank_bit0 = parity(norm_addr & (bank0_hash_bit_en << 7)) ^ cut_bits(norm_addr, bank0_intlv_bit, bank0_intlv_bit)

        bank = bank_bit3 * 8 + bank_bit2 * 4 + bank_bit1 * 2 + bank_bit0 * 1
        bg = bank // 4
        bs = bank % 4

        rankintlvbit = 0
        if cs_hit_base0 == 1:
            rankintlvbit = find_zero_lsb(cfg_base_mask_38_12[0]) + 12
        elif cs_hit_ext_base0 == 1:
            rankintlvbit = find_zero_lsb(cfg_ext_base_mask_38_12[0]) + 12
        elif cs_hit_base1 == 1:
            rankintlvbit = find_zero_lsb(cfg_base_mask_38_12[1]) + 12
        elif cs_hit_ext_base1 == 1:
            rankintlvbit = find_zero_lsb(cfg_ext_base_mask_38_12[1]) + 12

        if ((two_rank == 1) & cfg_rank_interleave_en):
            req_addr = (cut_bits(norm_addr, 32, rankintlvbit + 1) << rankintlvbit) + (
                cut_bits(norm_addr, rankintlvbit - 1, 0)
            )
        else:
            req_addr = norm_addr

        if cfg_addr_mode[rank] == 0b010000:
            row = cut_bits(req_addr, 27, 15)
        elif cfg_addr_mode[rank] == 0b011000:
            row = cut_bits(req_addr, 27, 15)
        elif cfg_addr_mode[rank] == 0b110000:
            row = cut_bits(req_addr, 27, 15)
        elif cfg_addr_mode[rank] == 0b010001:
            row = cut_bits(req_addr, 28, 15)
        elif cfg_addr_mode[rank] == 0b011001:
            row = cut_bits(req_addr, 28, 15)
        elif cfg_addr_mode[rank] == 0b110001:
            row = cut_bits(req_addr, 28, 15)
        elif cfg_addr_mode[rank] == 0b010010:
            row = cut_bits(req_addr, 29, 15)
        elif cfg_addr_mode[rank] == 0b011010:
            row = cut_bits(req_addr, 29, 15)
        elif cfg_addr_mode[rank] == 0b110010:
            row = cut_bits(req_addr, 29, 15)
        elif cfg_addr_mode[rank] == 0b010011:
            row = cut_bits(req_addr, 30, 15)
        elif cfg_addr_mode[rank] == 0b011011:
            row = cut_bits(req_addr, 30, 15)
        elif cfg_addr_mode[rank] == 0b110011:
            row = cut_bits(req_addr, 30, 15)
        elif cfg_addr_mode[rank] == 0b010100:
            row = cut_bits(req_addr, 31, 15)
        elif cfg_addr_mode[rank] == 0b011100:
            row = cut_bits(req_addr, 31, 15)
        elif cfg_addr_mode[rank] == 0b110100:
            row = cut_bits(req_addr, 31, 15)
        else:
            raise ValueError("AddrMode{0} {1} is not supported".format(rank, cfg_addr_mode[rank]))

        norm_addr = ((hole_removed_addr >> (intlv_granule + intlv_en)) << intlv_granule) + (
            cut_bits(hole_removed_addr, intlv_granule - 1, 0)
        )

        if bank16opt4 == 1:
            col = (cut_bits(req_addr, 11, 9) << 7) + (cut_bits(req_addr, 7, 1))
        elif bank16opt1 == 1:
            col = (cut_bits(req_addr, 14, 14) << 9) + (cut_bits(req_addr, 10, 7) << 5) + (cut_bits(req_addr, 5, 1))
        else:
            col = cfg_reduce_page_size_en

        col_value = col >> 4
        bur = col & 0xF

        result.append(
            DecodeResult(
                Physical_addr=hex(system_addr),
                Normalized_addr=hex(norm_addr),
                CH=ch,
                Rank=rank % 2,
                BankGroup=bg,
                Bank=bs,
                Row=row,
                Col=col_value,
                Bur=hex(bur),
            ).to_legacy_dict()
        )

    print(result)
    return result, excel_data
