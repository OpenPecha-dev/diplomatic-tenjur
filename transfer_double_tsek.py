import re
from antx import transfer

from pathlib import Path


def transfer_double_tsek(vol_without_tsek, vol_with_tsek):
    google_body_with_tsek = transfer(
        vol_with_tsek,[
        ["double_tseg",r"(:)"],
        ],
        vol_without_tsek,
        output="txt",
    )
    return google_body_with_tsek

def rm_extra_tsek(vol_with_tsek):
    vol_with_tsek = re.sub('(:)+', '\g<1>', vol_with_tsek)
    return vol_with_tsek

if __name__ == "__main__":
    vol_with_tsek_paths = list(Path('./P000791_with_tsek/').iterdir())
    vol_with_tsek_paths.sort()
    vol_without_tsek_paths = list(Path('./google_pedurma_hfmls/').iterdir())
    vol_without_tsek_paths.sort()
    for vol_with_tsek_path, vol_without_tsek_path in zip(vol_with_tsek_paths[14:20], vol_without_tsek_paths[14:20]):
        vol_with_tsek = vol_with_tsek_path.read_text(encoding='utf-8')
        vol_without_tsek = vol_without_tsek_path.read_text(encoding='utf-8')
        new_vol_with_tsek = transfer_double_tsek(vol_without_tsek, vol_with_tsek)
        new_vol_with_tsek = rm_extra_tsek(new_vol_with_tsek)
        Path(f'./google_pedurma_hfmls_with_tsek/{vol_with_tsek_path.stem}.txt').write_text(new_vol_with_tsek, encoding='utf-8')
        print(f'{vol_with_tsek_path.stem} completed..')
