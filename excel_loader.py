import atexit
import os
from pathlib import Path

import pandas as pd
import xlwings as xw

from .models import ChannelConfigInfo


class ExcelConfigRepository:
    def __init__(self, base_dir=None, workbook_name="SMC_TZConfig.xlsx"):
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).resolve().parent.parent
        self.file_path = self.base_dir / workbook_name
        self.app = xw.App(visible=False)
        self._wb_chconfig = xw.Book(self.file_path)
        self._df_chconfig = self._load_chconfig_df()
        atexit.register(self.close)

    def close(self):
        try:
            if self.app is not None:
                print("Exiting Python program - Excel app will be closed.")
                self.app.quit()
                self.app = None
        except Exception:
            self.app = None

    def _load_chconfig_df(self):
        ws_chconfig = self._wb_chconfig.sheets["CHConfig"]
        rng_chconfig = ws_chconfig.range("A1").expand().value

        df_chconfig = pd.DataFrame(rng_chconfig[0:])
        df_chconfig = df_chconfig.fillna("0x0")
        df_chconfig = df_chconfig.T
        df_chconfig.columns = df_chconfig.iloc[0]
        df_chconfig = df_chconfig[1:]
        return df_chconfig

    def get_project_list(self):
        return self._df_chconfig["Project_Code"].tolist()

    def make_project_df(self, project_name):
        wb = xw.Book(self.file_path)
        ws = wb.sheets[project_name]
        rng = ws.range("A1").expand().value
        df = pd.DataFrame(rng[0:])
        df.set_index(df.columns[0], inplace=True)
        df = df.fillna("0x0")
        return df

    def get_channel_config_info(self, project_code):
        row = self._df_chconfig[self._df_chconfig["Project_Code"] == project_code]
        return ChannelConfigInfo(
            Project_Code=row["Project_Code"].iloc[0],
            Project_Name=row["Project_Name"].iloc[0],
            CHASYM=int(row["CHASYM"].iloc[0]),
            CH_num=int(row["CH_num"].iloc[0]),
            CH_Bit2Hash=row["CH_Bit2Hash"].iloc[0],
            CH_Bit1Hash=row["CH_Bit1Hash"].iloc[0],
            CH_Bit0Hash=row["CH_Bit0Hash"].iloc[0],
            Bank3HashBitEn=row["Bank3HashBitEn"].iloc[0],
            Bank2HashBitEn=row["Bank2HashBitEn"].iloc[0],
            Bank1HashBitEn=row["Bank1HashBitEn"].iloc[0],
            Bank0HashBitEn=row["Bank0HashBitEn"].iloc[0],
        )
