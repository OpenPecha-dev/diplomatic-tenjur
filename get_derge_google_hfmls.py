import logging
import re
from horology import timed
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
        file_name = None
        if derge_vol_info:
            file_name = derge_vol_info['file_name']
        if file_name != None:
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
    if (len(g_page) - len(dg_page) > 700) or "བསྡུར་འབྲས" in g_page or "བསྡུར་མཆན" in g_page:
        return True
    else:
        return False

def rm_annotations(text, annotations):
    clean_text = text
    for ann in annotations:
        clean_text = re.sub(ann, '', clean_text)
    return clean_text

@timed(unit="min")
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

def transfer_pedurma_marker(vol_with_marker, vol_without_marker):
    # vol_without_marker = rm_annotations(vol_without_marker, [r"\[[𰵀-󴉱]?[0-9]+[a-z]{1}\]"])
    google_body_with_marker = transfer(
        vol_with_marker,[
        ["marker",r"(#)"],
        ],
        vol_without_marker,
        output="txt",
    )
    return google_body_with_marker

@timed(unit="min")
def get_derge_google_vol(pedurma_vol, derge_vol_mapping, pedurma_vol_num):
    derge_google_vol = ""
    derge_hfmls = ""
    derge_vols = match_derge_vol(pedurma_vol, derge_vol_mapping)
    for derge_vol in derge_vols:
        # derge_hfmls += f"{Path(f'./derge_hfmls/{derge_vol}.txt').read_text(encoding='utf-8')}\n"
        derge_hfmls += f"{Path(f'./hfmls/P000002/{derge_vol}').read_text(encoding='utf-8')}\n"
    logging.info(f'Derge vol {" &".join(derge_vols)} merged to form pedurma {pedurma_vol_num}..')
    # pedurma_hfml = Path(f'./google_pedurma_hfmls_with_tsek/{pedurma_vol_num}.txt').read_text(encoding='utf-8')
    pedurma_hfml = Path(f'./hfmls/12d32eb31c1a4cc59741cda99ebc7211/{pedurma_vol_num}.txt').read_text(encoding='utf-8')
    # derge_google_vol = transfer_pg_br(derge_hfmls, pedurma_hfml)
    derge_google_vol = transfer_pedurma_marker(derge_hfmls, pedurma_hfml)
    return derge_google_vol

@timed(unit="min")
def rm_extra_tsek(vol_with_tsek):
    vol_with_tsek = re.sub('(:)+', '\g<1>', vol_with_tsek)
    return vol_with_tsek

@timed(unit="min")
def build_derge_google_pedurma(pedurma_vol_mapping, derge_vol_mapping):
    nalanda_vols = ['v001','v003', 'v004', 'v005', 'v011', 'v012', 'v013', 'v014', 'v015', 'v016', 'v018', 'v019', 'v021', 'v022', 'v024', 'v025', 'v026', 'v027', 'v028', 'v033', 'v034', 'v036', 'v037', 'v038', 'v039', 
                    'v040', 'v041', 'v049', 'v051', 'v052', 'v053', 'v055', 'v056', 'v057', 'v058', 'v060', 'v061', 'v062', 'v063', 'v064', 'v065', 'v066', 'v067', 'v070', 'v071', 'v073', 'v075', 'v076', 'v077', 'v078',
                    'v079', 'v082', 'v083', 'v088', 'v089', 'v092', 'v093', 'v094', 'v096', 'v097', 'v098', 'v105', 'v106', 'v107', 'v108', 'v111', 'v114', 'v116']
    nalanda_vols = ['v075']
    for vol_id, pedurma_vol in pedurma_vol_mapping.items():
        pedurma_vol_num = f'v{int(vol_id):03}'
        print(f'{pedurma_vol_num} processing...')
        derge_google_vol_path = Path(f'./google_pedurma_hfmls_with_marker/{pedurma_vol_num}.txt')
        # derge_google_vol_path = Path(f'./derge_google_pedurma/{pedurma_vol_num}.txt')
        if derge_google_vol_path.is_file():
            print(f'INFO: {pedurma_vol_num} completed..')
            continue
        if pedurma_vol_num in nalanda_vols:
            derge_google_vol = get_derge_google_vol(pedurma_vol, derge_vol_mapping, pedurma_vol_num)
            derge_google_vol = rm_extra_tsek(derge_google_vol)
            derge_google_vol_path.write_text(derge_google_vol, encoding='utf-8')
        print(f'INFO: {pedurma_vol_num} completed..')

if __name__ == "__main__":
    pedurma_vol_mapping = yaml.safe_load(Path('./pedurma_vol_mapping.yml').read_text(encoding='utf'))
    derge_vol_mapping = yaml.safe_load(Path('./new_derge_vol_mapping.yml').read_text(encoding='utf'))
    build_derge_google_pedurma(pedurma_vol_mapping, derge_vol_mapping)
    # derge_google_hfml_paths = list(Path('./derge_google_pedurma').iterdir())
    # annotations= [r"\{([𰵀-󴉱])?\w+\}"]
    # for derge_google_hfml_path in derge_google_hfml_paths:
    #     hfml = derge_google_hfml_path.read_text(encoding='utf-8')
    #     new_hfml = rm_annotations(hfml, annotations)
    #     Path(f'P000791/{derge_google_hfml_path.stem}.txt').write_text(new_hfml, encoding='utf-8')

