import re
import yaml
from collections import defaultdict
from pathlib import Path
from typing import List, Optional


from antx import transfer
from openpecha.cli import download_pecha
from openpecha.serializers import HFMLSerializer
from pydantic import BaseModel

from pedurma.pecha import *
from pedurma.preprocess import get_derge_google_text

def from_yaml(yml_path):
    return yaml.safe_load(yml_path.read_text(encoding="utf-8"))


def get_text_info(text_id, index):
    texts = index["annotations"]
    for uuid, text in texts.items():
        if text["work_id"] == text_id:
            return (uuid, text)
    return ("", "")


def get_meta_data(pecha_id, text_uuid, meta_data):
    meta = {}

    meta = {
        "work_id": meta_data.get("work_id", ""),
        "img_grp_offset": meta_data.get("img_grp_offset",""),
        "pref": meta_data.get("pref", ""),
        "pecha_id": pecha_id,
        "text_uuid": text_uuid,
    }
    return meta


def get_hfml_text(opf_path, text_id, index=None):
    serializer = HFMLSerializer(opf_path, text_id=text_id, index_layer=index, layers=['Pagination', 'Durchen'])
    serializer.apply_layers()
    hfml_text = serializer.get_result()
    return hfml_text

def get_prev_pg_ann(pg_num, pg_face):
    prev_pg_ann = '['
    if pg_face == 'a':
        prev_pg_ann += f'{pg_num-1}b]'
    else:
        prev_pg_ann += f'{pg_num}b]'
    return prev_pg_ann

def add_first_page_ann(text):
    pg_pat = re.search(r"\[[𰵀-󴉱]?([0-9]+)([a-z]{1})\]", text)
    pg_num = pg_pat.group(1)
    pg_face = pg_pat.group(2)
    prev_pg_ann = get_prev_pg_ann(pg_num, pg_face)
    new_text = f'{prev_pg_ann}\n{text}'
    return new_text


def get_body_text(text_with_durchen):
    try:
        durchen_starting = re.search("<[𰵀-󴉱]?d", text_with_durchen).start()
        text_content = text_with_durchen[:durchen_starting]
    except Exception:
        text_content = text_with_durchen
    return text_content


def get_durchen(text_with_durchen):
    durchen = ""
    durchen_start = False
    pages = get_pages(text_with_durchen)
    for page in pages:
        if re.search("<[𰵀-󴉱]?d", page) or durchen_start == True:
            durchen += page
            durchen_start = True
        if re.search('d>', page):
            return durchen
    if not durchen:
        print('INFO: durchen not found..')
    return durchen


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


def get_page_id(page_idx, pagination_layer):
    paginations = pagination_layer["annotations"]
    for uuid, pagination in paginations.items():
        if pagination["page_index"] == page_idx:
            return (uuid, pagination)
    return ("", "")


def get_page_num(page_ann):
    pg_num = int(page_ann[:-1]) * 2
    pg_face = page_ann[-1]
    if pg_face == "a":
        pg_num -= 1
    return pg_num


def get_link(pg_num, text_meta):
    vol = text_meta["vol"]
    img_group_offset = text_meta["img_grp_offset"]
    pref = text_meta["pref"]
    igroup = f"{pref}{img_group_offset+vol}"
    link = f"https://iiif.bdrc.io/bdr:{igroup}::{igroup}{int(pg_num):04}.jpg/full/max/0/default.jpg"
    return link


def get_note_ref(pagination):
    try:
        return pagination["note_ref"]
    except Exception:
        return ""


def get_clean_page(page):
    pat_list = {
            "page_pattern": r"\[([𰵀-󴉱])?[0-9]+[a-z]{1}\]",
            "topic_pattern": r"\{([𰵀-󴉱])?\w+\}",
            "start_durchen_pattern": r"\<([𰵀-󴉱])?d",
            "end_durchen_pattern": r"d\>",
            "sub_topic_pattern": r"\{([𰵀-󴉱])?\w+\-\w+\}",
        }
    base_page = page
    for ann, ann_pat in pat_list.items():
        base_page = re.sub(ann_pat, "", base_page)
    return base_page


def get_page_obj(page, text_meta, tag, pagination_layer):
    page_idx = re.search(r"\[([𰵀-󴉱])?([0-9]+[a-z]{1})\]", page).group(2)
    page_id, pagination = get_page_id(page_idx, pagination_layer)
    page_content = get_clean_page(page)
    pg_num = get_page_num(page_idx)
    page_link = get_link(pg_num, text_meta)
    note_ref = get_note_ref(pagination)
    if page_content == "\n":
        page_obj = None
    else:
        if tag == "note":
            page_obj = NotesPage(
                id=page_id,
                page_no=pg_num,
                content=page_content,
                name=f"Page {pg_num}",
                vol=text_meta["vol"],
                image_link=page_link,
            )
        else:
            page_obj = Page(
                id=page_id,
                page_no=pg_num,
                content=page_content,
                name=f"Page {pg_num}",
                vol=text_meta["vol"],
                image_link=page_link,
                note_ref=note_ref,
            )

    return page_obj


def get_page_obj_list(text, text_meta, pagination_layer, tag="text"):
    page_obj_list = []
    pages = get_pages(text)
    for page in pages:
        pg_obj = get_page_obj(page, text_meta, tag, pagination_layer)
        if pg_obj:
            page_obj_list.append(pg_obj)
    return page_obj_list


def construct_text_obj(hfmls, text_meta, opf_path):
    pages = []
    notes = []
    vol_span = []
    for vol_num, hfml_text in hfmls.items():
        text_meta["vol"] = int(vol_num[1:])
        pagination_layer = from_yaml(
            Path(
                f"{opf_path}/{text_meta['pecha_id']}.opf/layers/v{int(text_meta['vol']):03}/Pagination.yml"
            )
        )
        if not re.search(r"\[([𰵀-󴉱])?([0-9]+[a-z]{1})\]", hfml_text[:10]):
            hfml_text = add_first_page_ann(hfml_text)
        body_text = get_body_text(hfml_text)
        durchen = get_durchen(hfml_text)
        pages += get_page_obj_list(body_text, text_meta, pagination_layer, tag="text")
        if durchen:
            notes += get_page_obj_list(durchen, text_meta, pagination_layer, tag="note")
    text_obj = Text(id=text_meta["text_uuid"], pages=pages, notes=notes)
    return text_obj


def serialize_text_obj(text):
    text_hfml = defaultdict(str)
    pages = text.pages
    notes = text.notes
    for page in pages:
        text_hfml[f"v{int(page.vol):03}"] += page.content
    for note in notes:
        text_hfml[f"v{int(note.vol):03}"] += note.content
    return text_hfml

def get_derge_google_text_obj(text_id):
    dg_hfmls = {}
    derge_pecha_id = "P000002"
    google_pecha_id = "P000791"
    derge_pecha_path = download_pecha(derge_pecha_id, needs_update=False)
    derge_hfmls = get_hfml_text(f"{derge_pecha_path}/{derge_pecha_id}.opf/", text_id)
    google_pecha_path = download_pecha(google_pecha_id, needs_update=False)
    google_meta_data = from_yaml(Path(f"{google_pecha_path}/{google_pecha_id}.opf/meta.yml"))
    google_index = from_yaml(Path(f"{google_pecha_path}/{google_pecha_id}.opf/index.yml"))
    google_hfmls = get_hfml_text(f"{google_pecha_path}/{google_pecha_id}.opf/", text_id, google_index)
    text_uuid, google_text = get_text_info(text_id, google_index)
    google_text_meta = get_meta_data(google_pecha_id, text_uuid, google_meta_data)
    for (vol_id, d_hfml),(v_id, g_hfml) in zip(derge_hfmls.items(), google_hfmls.items()):
        dg_hfmls[v_id] = get_derge_google_text(d_hfml, g_hfml)
    dg_text = construct_text_obj(dg_hfmls, google_text_meta, google_pecha_path)
    return dg_text

def get_text_obj(pecha_id, text_id, pecha_path = None):
    if not pecha_path:
        pecha_path = download_pecha(pecha_id, needs_update=False)
    meta_data = from_yaml(Path(f"{pecha_path}/{pecha_id}.opf/meta.yml"))
    index = from_yaml(Path(f"{pecha_path}/{pecha_id}.opf/index.yml"))
    hfmls = get_hfml_text(f"{pecha_path}/{pecha_id}.opf/", text_id, index)
    text_uuid, text = get_text_info(text_id, index)
    text_meta = get_meta_data(pecha_id, text_uuid, meta_data)
    text = construct_text_obj(hfmls, text_meta, pecha_path)
    return text


# if __name__ == "__main__":
#     text_id = 'D1118'
#     pecha_id = 'P000792'
#     opf_path = f'./test/{pecha_id}.opf'
#     index = from_yaml(Path(f"./test/{pecha_id}.opf/index.yml"))
#     meta_data = from_yaml(Path(f"./test/{pecha_id}.opf/meta.yml"))
#     text_uuid, text_info = get_text_info(text_id, index)
#     text_meta = get_meta_data(pecha_id, text_uuid, meta_data)
#     hfmls = get_hfml_text(text_id, opf_path)
#     text_obj = get_text_obj(hfmls, text_meta, opf_path)
