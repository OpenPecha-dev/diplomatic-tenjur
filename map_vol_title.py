import re
import yaml
from pathlib import Path
from pyewts import pyewts


converter = pyewts()


def parse_vol_info(vol_info):
    sub_vols = []
    vol_info_parts = vol_info.split(' ')
    if len(vol_info_parts) == 7:
        sub_vols.append(f'{vol_info_parts[3]} {vol_info_parts[4]}')
        if len(vol_info_parts[5]) > 3:
            sub_vols.append(f'{vol_info_parts[5]} {vol_info_parts[6]}')
        else:
            sub_vols.append(f'{vol_info_parts[3]} {vol_info_parts[5]}')
            sub_vols.append(f'{vol_info_parts[3]} {vol_info_parts[6]}')
    elif len(vol_info_parts) == 6:
        sub_vols.append(f'{vol_info_parts[3]} {vol_info_parts[4]}')
        sub_vols.append(f'{vol_info_parts[3]} {vol_info_parts[5]}')
    elif len(vol_info_parts) == 5:
        sub_vols.append(f'{vol_info_parts[3]} {vol_info_parts[4]}')
    return sub_vols

def extract_pedurma_vol_info(pedurma_vol_titles):
    pedurma_vols = {}
    vol_infos = pedurma_vol_titles.splitlines()
    for vol_num, vol_info in enumerate(vol_infos, 1):
        pedurma_vols[f'{vol_num}'] = parse_vol_info(vol_info)
    return pedurma_vols

def clean_title(title):
    title = re.sub('\d+_', '', title)
    title = re.sub('_', ' ', title)
    title = re.sub('འགྲེལ', '', title)
    return title

def derge_title_update(derge_vol_mapping):
    new_derge_vol_mapping = {}
    vol_paths = list(Path('./derge_hfmls/').iterdir())
    vol_paths.sort()
    vol_titles = [vol_path.stem for vol_path in vol_paths]
    for (vol_num, vol_info), vol_title in zip(derge_vol_mapping.items(), vol_titles):
        derge_vol_mapping[vol_num]['bdrc'] = vol_info['bdrc']
        derge_vol_mapping[vol_num]['vol'] = clean_title(vol_title)
        derge_vol_mapping[vol_num]['file_name'] = vol_title
    return derge_vol_mapping


if __name__ == "__main__":
    pedurma_vol_titles = Path('./pedurma_vol_titles.txt').read_text(encoding='utf-8')
    peduma_vols = extract_pedurma_vol_info(pedurma_vol_titles)
    derge_vols = yaml.safe_load(Path('./derge_vol_mapping.yml').read_text(encoding='utf-8'))
    new_derge_vols = derge_title_update(derge_vols)
    new_derge_vols = yaml.safe_dump(new_derge_vols, sort_keys=False, allow_unicode=True)
    Path('./new_derge_vol_mapping.yml').write_text(new_derge_vols, encoding='utf-8')
