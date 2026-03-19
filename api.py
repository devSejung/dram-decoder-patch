from .decoder_core import decode_addresses, get_memory_configuration_list as build_memory_configuration_list
from .excel_loader import ExcelConfigRepository
from .models import DecodeContext


_repository = None


def _get_repository():
    global _repository
    if _repository is None:
        _repository = ExcelConfigRepository()
    return _repository


def close():
    global _repository
    if _repository is not None:
        _repository.close()
        _repository = None


def get_project_list():
    repo = _get_repository()
    return repo.get_project_list()


def get_memory_configuration_list(project_code):
    repo = _get_repository()
    info = repo.get_channel_config_info(project_code)
    df = repo.make_project_df(project_code)
    return build_memory_configuration_list(info, df)


def decode(project_code, mem_config, system_addrs):
    repo = _get_repository()
    excel_data = {}
    try:
        config = int(mem_config)
        info = repo.get_channel_config_info(project_code)
        df = repo.make_project_df(project_code)
        context = DecodeContext(
            project_code=project_code,
            config=config,
            excel_data=excel_data,
            info=info,
            project_df=df,
        )
        result, excel_data = decode_addresses(context, system_addrs)
        return None, result, excel_data
    except ValueError as e:
        print(f"An error occurred: {e}")
        return e, None, excel_data
