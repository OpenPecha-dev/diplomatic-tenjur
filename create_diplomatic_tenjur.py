import re
from pathlib import Path

from pedurma import *

DERGE_PECHA_ID ="P000002"
G_PEDURMA_ID = "P000792"
DIPLOMATIC_TENJUR_ID = "P000999"

DERGE_OPF_PATH = Path("./opfs/P000002/")
G_PEDURMA_OPF_PATH = Path("./opfs/P000792/")
DIPLOMATIC_TENJUR_PATH = Path('./opfs/P000999/')

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
    if (len(g_page) - len(dg_page) > 1000) or re.search("<[𰵀-󴉱]?d", g_page) or "བསྡུར་འབྲས" in g_page:
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
    anns = [r"\n", r"\[\w+\.\d+\]", r"\[[𰵀-󴉱]?[0-9]+[a-z]{1}\]"]
    derge_hfml = rm_annotations(derge_hfml, anns)
    dg_body = transfer(
        google_hfml,
        [["linebreak", r"(\n)"], ["pg_ann", r"(\[[𰵀-󴉱]?[0-9]+[a-z]{1}\])"]],
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

def get_derge_google_text(derge_hfmls, google_hfmls, g_text_meta):
    derge_google_hfmls = {}
    for (_, derge_hfml), (vol_id, google_hfml) in zip(derge_hfmls.items(), google_hfmls.items()):
        derge_google_hfmls[vol_id] = transfer_pg_br(derge_hfml, google_hfml)
    for vol_id, text in derge_google_hfmls.items():
        Path(f'./hfmls/derge_google_hfml_{vol_id}.txt').write_text(text, encoding='utf-8')
    derge_google_text = construct_text_obj(derge_google_hfmls, g_text_meta, G_PEDURMA_OPF_PATH)
    return derge_google_text


def update_diplomat_tenjur(text_id):
    google_pecha_idx = yaml.safe_load((G_PEDURMA_OPF_PATH / f'{G_PEDURMA_ID}.opf/index.yml').read_text(encoding='utf-8'))
    g_meta = yaml.safe_load((G_PEDURMA_OPF_PATH / f'{G_PEDURMA_ID}.opf/meta.yml').read_text(encoding='utf-8'))
    derge_hfmls = get_hfml_text(DERGE_OPF_PATH / f'{DERGE_PECHA_ID}.opf/', text_id)
    google_hfmls = get_hfml_text(G_PEDURMA_OPF_PATH / f'{G_PEDURMA_ID}.opf/', text_id, google_pecha_idx)
    g_text_uuid, g_text = get_text_info(text_id, google_pecha_idx)
    g_text_meta = get_meta_data(G_PEDURMA_ID, g_text_uuid, g_meta)
    derge_googel_text = get_derge_google_text(derge_hfmls, google_hfmls, g_text_meta)
    old_pecha_idx = yaml.safe_load((DIPLOMATIC_TENJUR_PATH / f'{DIPLOMATIC_TENJUR_ID}.opf/index.yml').read_text(encoding='utf-8'))
    prev_pecha_idx = copy.deepcopy(old_pecha_idx)
    new_pecha_idx = update_index(DIPLOMATIC_TENJUR_PATH, DIPLOMATIC_TENJUR_ID, derge_googel_text, old_pecha_idx)
    update_old_layers(DIPLOMATIC_TENJUR_PATH, DIPLOMATIC_TENJUR_ID, derge_googel_text, prev_pecha_idx)
    update_base(DIPLOMATIC_TENJUR_PATH, DIPLOMATIC_TENJUR_ID, derge_googel_text, prev_pecha_idx)
    new_pecha_idx = yaml.safe_dump(new_pecha_idx, sort_keys=False)
    (DIPLOMATIC_TENJUR_PATH / f'{DIPLOMATIC_TENJUR_ID}.opf/index.yml').write_text(new_pecha_idx, encoding='utf-8')

if __name__ == "__main__":
    text_id = "D1346"
    update_diplomat_tenjur(text_id)
