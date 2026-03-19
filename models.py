from dataclasses import dataclass
from typing import Dict, List


@dataclass
class ChannelConfigInfo:
    Project_Code: str
    Project_Name: str
    CHASYM: int
    CH_num: int
    CH_Bit2Hash: str
    CH_Bit1Hash: str
    CH_Bit0Hash: str
    Bank3HashBitEn: str
    Bank2HashBitEn: str
    Bank1HashBitEn: str
    Bank0HashBitEn: str

    def to_dict(self) -> Dict[str, object]:
        return {
            "Project_Code": self.Project_Code,
            "Project_Name": self.Project_Name,
            "CHASYM": self.CHASYM,
            "CH_num": self.CH_num,
            "CH_Bit2Hash": self.CH_Bit2Hash,
            "CH_Bit1Hash": self.CH_Bit1Hash,
            "CH_Bit0Hash": self.CH_Bit0Hash,
            "Bank3HashBitEn": self.Bank3HashBitEn,
            "Bank2HashBitEn": self.Bank2HashBitEn,
            "Bank1HashBitEn": self.Bank1HashBitEn,
            "Bank0HashBitEn": self.Bank0HashBitEn,
        }


@dataclass
class DecodeContext:
    project_code: str
    config: int
    excel_data: Dict[str, object]
    info: ChannelConfigInfo
    project_df: object


@dataclass
class DecodeResult:
    Physical_addr: str
    Normalized_addr: str
    CH: int
    Rank: int
    BankGroup: int
    Bank: int
    Row: int
    Col: int
    Bur: str

    def to_legacy_dict(self) -> Dict[str, object]:
        return {
            "Physical_addr": self.Physical_addr,
            "Normalized_addr": self.Normalized_addr,
            "CH": self.CH,
            "Rank": self.Rank,
            "BankGroup": self.BankGroup,
            "Bank": self.Bank,
            "Row": self.Row,
            "Col": self.Col,
            "Bur": self.Bur,
        }


@dataclass
class ProjectThresholdRule:
    project_code: str
    total_density_thresholds: Dict[int, int]


DEFAULT_LPDDR5_SUBCHANNEL = None
