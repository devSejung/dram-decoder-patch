import importlib

import dram_decoder


def compare(project_code, mem_config, system_addrs):
    legacy = importlib.import_module("decoder")

    legacy_error, legacy_result, legacy_excel_data = legacy.decode(project_code, mem_config, system_addrs)
    new_error, new_result, new_excel_data = dram_decoder.decode(project_code, mem_config, system_addrs)

    return {
        "legacy_error": legacy_error,
        "legacy_result": legacy_result,
        "legacy_excel_data": legacy_excel_data,
        "new_error": new_error,
        "new_result": new_result,
        "new_excel_data": new_excel_data,
        "result_match": legacy_result == new_result,
        "excel_data_match": legacy_excel_data == new_excel_data,
        "error_match": str(legacy_error) == str(new_error),
    }
