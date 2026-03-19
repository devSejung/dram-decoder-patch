from .models import ProjectThresholdRule


ASYM_REGION_RULES = {
    "S5AV920_8CH": ProjectThresholdRule(
        project_code="S5AV920_8CH",
        total_density_thresholds={
            14: int("0xB_0000_0000", 16),
            18: int("0xB_0000_0000", 16),
            20: int("0xC_0000_0000", 16),
            28: int("0xE_0000_0000", 16),
        },
    ),
    "S5AV620_4CH": ProjectThresholdRule(
        project_code="S5AV620_4CH",
        total_density_thresholds={
            10: int("0xA_0000_0000", 16),
            14: int("0xB_0000_0000", 16),
            18: int("0xB_0000_0000", 16),
            20: int("0xC_0000_0000", 16),
            28: int("0xE_0000_0000", 16),
        },
    ),
    "S5AV920_4CH": ProjectThresholdRule(
        project_code="S5AV920_4CH",
        total_density_thresholds={
            10: int("0xA_0000_0000", 16),
            14: int("0xB_0000_0000", 16),
            18: int("0xB_0000_0000", 16),
            20: int("0xC_0000_0000", 16),
            28: int("0xE_0000_0000", 16),
        },
    ),
    "S5AV930": ProjectThresholdRule(
        project_code="S5AV930",
        total_density_thresholds={
            20: int("0xC_0000_0000", 16),
            28: int("0xE_0000_0000", 16),
            40: int("0x88_0000_0000", 16),
            56: int("0x8C_0000_0000", 16),
        },
    ),
}


def resolve_asym_region(project_code, total_density, system_addr):
    rule = ASYM_REGION_RULES.get(project_code)
    if rule is None:
        return 0

    threshold = rule.total_density_thresholds.get(total_density)
    if threshold is None:
        return 0

    return 1 if system_addr >= threshold else 0
