import logging
import re
import yaml
from antx import transfer
from pathlib import Path

root_logger= logging.getLogger()
root_logger.setLevel(logging.DEBUG) # or whatever
handler = logging.FileHandler('vol_mapping.log', 'w', 'utf-8') # or whatever
handler.setFormatter(logging.Formatter('%(name)s %(message)s')) # or whatever
root_logger.addHandler(handler)

def match_derge_vol(pedurma_vol, derge_vol_mapping):
    derge_vols = []
    for pedurma_sub_vol in pedurma_vol:
        derge_vol_info = derge_vol_mapping.get(pedurma_sub_vol, {})
        if derge_vol_info:
            file_name = derge_vol_info['file_name']
        if file_name:
            derge_vols.append(file_name)
    return derge_vols

def get_pages(vol_text):
    result = []
    pg_text = ""
    pages = re.split(r"(\[[𰵀-󴉱]?[0-9]+[a-z]{1}\])", vol_text)
    for i, page in enumerate(pages[1:]):
        if i % 2 == 0:
            pg_text += page
        else:
            pg_text += page
            result.append(pg_text)
            pg_text = ""
    return result


def is_note_page(g_page, dg_page):
    if (len(g_page) - len(dg_page) > 700) or re.search("<[𰵀-󴉱]?d", g_page) or "བསྡུར་འབྲས" in g_page:
        return True
    else:
        return False

def  rm_annotations(text, annotations):
    clean_text = text
    for ann in annotations:
        clean_text = re.sub(ann, '', clean_text)
    return clean_text

def transfer_pg_br(derge_hfml, google_hfml):
    derge_google_text = ""
    anns = [r"\n", r"\[\w+\.\d+\]", r"\[[𰵀-󴉱]?[0-9]+[a-z]{1}\]", r"\{([𰵀-󴉱])?\w+\}",  r"\{([𰵀-󴉱])?\w+\-\w+\}"]
    derge_hfml = rm_annotations(derge_hfml, anns)
    dg_body = transfer(
        google_hfml,
        [["linebreak", r"(\n)"], 
        ["pg_ann", r"(\[[𰵀-󴉱]?[0-9]+[a-z]{1}\])"],
        ["double_tseg",r"(:)"],
        ],
        derge_hfml,
        output="txt",
    )
    dg_pages = get_pages(dg_body)
    g_pages = get_pages(google_hfml)
    for g_page, dg_page in zip(g_pages, dg_pages):
        if is_note_page(g_page, dg_page):
            derge_google_text += g_page
        else:
            derge_google_text += dg_page
    return derge_google_text

def get_derge_google_vol(pedurma_vol, derge_vol_mapping, pedurma_vol_num):
    derge_google_vol = ""
    derge_hfmls = ""
    derge_vols = match_derge_vol(pedurma_vol, derge_vol_mapping)
    for derge_vol in derge_vols:
        derge_hfmls += f"{Path(f'./derge_hfmls/{derge_vol}.txt').read_text(encoding='utf-8')}\n"
    logging.info(f'Derge vol {" &".join(derge_vols)} merged to form pedurma {pedurma_vol_num}..')
    pedurma_hfml = Path(f'./google_pedurma_hfmls_with_tsek/{pedurma_vol_num}.txt').read_text(encoding='utf-8')
    derge_google_vol = transfer_pg_br(derge_hfmls, pedurma_hfml)
    return derge_google_vol

def rm_extra_tsek(vol_with_tsek):
    vol_with_tsek = re.sub('(:)+', '\g<1>', vol_with_tsek)
    return vol_with_tsek

def build_derge_google_pedurma(pedurma_vol_mapping, derge_vol_mapping):
    for vol_id, pedurma_vol in pedurma_vol_mapping.items():
        pedurma_vol_num = f'v{int(vol_id):03}'
        print(f'{pedurma_vol_num} porcessing...')
        derge_google_vol_path = Path(f'./derge_google_pedurma/{pedurma_vol_num}.txt')
        if derge_google_vol_path.is_file():
            print(f'INFO: {pedurma_vol_num} completed..')
            continue
        if int(vol_id) > 41 and int(vol_id) < 49:
            continue
        derge_google_vol = get_derge_google_vol(pedurma_vol, derge_vol_mapping, pedurma_vol_num)
        derge_google_vol = rm_extra_tsek(derge_google_vol)
        derge_google_vol_path.write_text(derge_google_vol, encoding='utf-8')
        print(f'INFO: {pedurma_vol_num} completed..')

if __name__ == "__main__":
    pedurma_vol_mapping = yaml.safe_load(Path('./pedurma_vol_mapping.yml').read_text(encoding='utf'))
    derge_vol_mapping = yaml.safe_load(Path('./new_derge_vol_mapping.yml').read_text(encoding='utf'))
    build_derge_google_pedurma(pedurma_vol_mapping, derge_vol_mapping)

