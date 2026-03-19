def load_primary_config(df, config, target):
    target["rank_num"][0] = int(df[config]["rank_num"])
    target["rank0_density"][0] = int(df[config]["rank0_density"])
    target["rank1_density"][0] = int(df[config]["rank1_density"])
    target["BaseAddr0"][0] = int(df[config]["BaseAddr0"], 16)
    target["BaseAddr1"][0] = int(df[config]["BaseAddr1"], 16)
    target["BaseMask0"][0] = int(df[config]["BaseMask0"], 16)
    target["BaseMask1"][0] = int(df[config]["BaseMask1"], 16)
    target["ExtBaseAddr0"][0] = int(df[config]["ExtBaseAddr0"], 16)
    target["ExtBaseAddr1"][0] = int(df[config]["ExtBaseAddr1"], 16)
    target["ExtBaseMask0"][0] = int(df[config]["ExtBaseMask0"], 16)
    target["ExtBaseMask1"][0] = int(df[config]["ExtBaseMask1"], 16)
    target["AddrMapMode"][0] = int(df[config]["AddrMapMode"], 16)
    target["IntlvBaseAddr0"][0] = int(df[config]["IntlvBaseAddr0"], 16)
    target["IntlvBaseAddr1"][0] = int(df[config]["IntlvBaseAddr1"], 16)
    target["IntlvBaseMask0"][0] = int(df[config]["IntlvBaseMask0"], 16)
    target["IntlvBaseMask1"][0] = int(df[config]["IntlvBaseMask1"], 16)
    target["TzSpare"][0] = int(df[config]["TzSpare"], 16)

    _try_load(df, config, "ExtIntlvBaseAddr0", target["ExtIntlvBaseAddr0"], 0, 16)
    _try_load(df, config, "ExtIntlvBaseAddr1", target["ExtIntlvBaseAddr1"], 0, 16)
    _try_load(df, config, "ExtIntlvBaseMask0", target["ExtIntlvBaseMask0"], 0, 16)
    _try_load(df, config, "ExtIntlvBaseMask1", target["ExtIntlvBaseMask1"], 0, 16)


def load_asym_config(df, config, target):
    _try_load(df, config, "ASYM_rank_num", target["rank_num"], 1)
    _try_load(df, config, "ASYM_rank0_density", target["rank0_density"], 1)
    _try_load(df, config, "ASYM_rank1_density", target["rank1_density"], 1)
    _try_load(df, config, "ASYM_BaseAddr0", target["BaseAddr0"], 1, 16)
    _try_load(df, config, "ASYM_BaseAddr1", target["BaseAddr1"], 1, 16)
    _try_load(df, config, "ASYM_BaseMask0", target["BaseMask0"], 1, 16)
    _try_load(df, config, "ASYM_BaseMask1", target["BaseMask1"], 1, 16)
    _try_load(df, config, "ASYM_ExtBaseAddr0", target["ExtBaseAddr0"], 1, 16)
    _try_load(df, config, "ASYM_ExtBaseAddr1", target["ExtBaseAddr1"], 1, 16)
    _try_load(df, config, "ASYM_ExtBaseMask0", target["ExtBaseMask0"], 1, 16)
    _try_load(df, config, "ASYM_ExtBaseMask1", target["ExtBaseMask1"], 1, 16)
    _try_load(df, config, "ASYM_AddrMapMode", target["AddrMapMode"], 1, 16)
    _try_load(df, config, "ASYM_IntlvBaseAddr0", target["IntlvBaseAddr0"], 1, 16)
    _try_load(df, config, "ASYM_IntlvBaseAddr1", target["IntlvBaseAddr1"], 1, 16)
    _try_load(df, config, "ASYM_IntlvBaseMask0", target["IntlvBaseMask0"], 1, 16)
    _try_load(df, config, "ASYM_IntlvBaseMask1", target["IntlvBaseMask1"], 1, 16)
    _try_load(df, config, "ASYM_TzSpare", target["TzSpare"], 1, 16)
    _try_load(df, config, "ASYM_ExtIntlvBaseAddr0", target["ExtIntlvBaseAddr0"], 1, 16)
    _try_load(df, config, "ASYM_ExtIntlvBaseAddr1", target["ExtIntlvBaseAddr1"], 1, 16)
    _try_load(df, config, "ASYM_ExtIntlvBaseMask0", target["ExtIntlvBaseMask0"], 1, 16)
    _try_load(df, config, "ASYM_ExtIntlvBaseMask1", target["ExtIntlvBaseMask1"], 1, 16)


def build_register_state():
    return {
        "rank_num": [0, 0],
        "rank0_density": [0, 0],
        "rank1_density": [0, 0],
        "BaseAddr0": [0, 0],
        "BaseAddr1": [0, 0],
        "BaseMask0": [0, 0],
        "BaseMask1": [0, 0],
        "ExtBaseAddr0": [0, 0],
        "ExtBaseAddr1": [0, 0],
        "ExtBaseMask0": [0, 0],
        "ExtBaseMask1": [0, 0],
        "AddrMapMode": [0, 0],
        "BankAddrMode": [0, 0],
        "IntlvBaseAddr0": [0, 0],
        "IntlvBaseAddr1": [0, 0],
        "IntlvBaseMask0": [0, 0],
        "IntlvBaseMask1": [0, 0],
        "TzSpare": [0, 0],
        "ExtIntlvBaseAddr0": [0, 0],
        "ExtIntlvBaseAddr1": [0, 0],
        "ExtIntlvBaseMask0": [0, 0],
        "ExtIntlvBaseMask1": [0, 0],
    }


def _try_load(df, config, key, target, index, base=10):
    try:
        target[index] = int(df[config][key], base)
    except Exception:
        pass
