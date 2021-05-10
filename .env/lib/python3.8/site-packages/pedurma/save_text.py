import copy
from openpecha.blupdate import *
from openpecha.cli import download_pecha
from pedurma.pecha import *
from pedurma.texts import serialize_text_obj

def get_old_vol(pecha_opf_path, pecha_id, text_vol_span):
    old_vols = {}
    for vol_id in text_vol_span:
        old_vols[vol_id] = (pecha_opf_path / f"{pecha_id}.opf/base/{vol_id}.txt").read_text(encoding='utf-8')
    return old_vols

def get_old_text_base(old_pecha_idx, old_vol_base, text_id, text_vol_num):
    text_span = old_pecha_idx['annotations'][text_id]['span']
    for vol_span in text_span:
        if vol_span['vol'] == text_vol_num:
            return old_vol_base[vol_span['start']:vol_span['end']]
    return ''

def get_new_vol(old_vols, old_pecha_idx, text_obj):
    new_vols = {}
    new_text = serialize_text_obj(text_obj)
    for vol_id, new_text_base in new_text.items():
        vol_num = int(vol_id[1:])
        old_vol_base = old_vols[vol_id]
        old_text_base = get_old_text_base(old_pecha_idx, old_vol_base, text_obj.id, vol_num)
        old_text_base = old_text_base.strip()
        new_text_base = new_text_base.strip()
        new_vol_base = old_vol_base.replace(old_text_base, new_text_base)
        new_vols[vol_id] = new_vol_base
    return new_vols

def get_text_vol_span(pecha_idx, text_uuid):
    text_vol_span = []
    for span in pecha_idx['annotations'][text_uuid]['span']:
        vol_num = span['vol']
        text_vol_span.append(f'v{int(vol_num):03}')
    return text_vol_span

def update_base(pecha_opf_path, pecha_id, text_obj, old_pecha_idx):
    text_vol_span = get_text_vol_span(old_pecha_idx, text_obj.id)
    old_vols = get_old_vol(pecha_opf_path, pecha_id, text_vol_span)
    new_vols = get_new_vol(old_vols, old_pecha_idx, text_obj)
    for vol_id, new_vol_base in new_vols.items():
        (pecha_opf_path / f"{pecha_id}.opf/base/{vol_id}.txt").write_text(new_vol_base, encoding='utf-8')
        print(f'INFO: {vol_id} base updated..')

def get_old_layers(pecha_opf_path, pecha_id, vol_id):
    old_layers = {}
    layer_paths = list((pecha_opf_path / f"{pecha_id}.opf/layers/{vol_id}").iterdir())
    for layer_path in layer_paths:
        layer_name = layer_path.stem
        layer_content = yaml.safe_load(layer_path.read_text(encoding='utf-8'))
        old_layers[layer_name] = layer_content
    return old_layers

def update_layer(pecha_opf_path, pecha_id, vol_id, old_layers, updater):
    for layer_name, old_layer in old_layers.items():
        update_ann_layer(old_layer, updater)
        new_layer = yaml.safe_dump(old_layer, sort_keys=False)
        (pecha_opf_path / f"{pecha_id}.opf/layers/{vol_id}/{layer_name}.yml").write_text(new_layer, encoding='utf-8')
        print(f'INFO: {vol_id} {layer_name} has been updated...')
    
def update_old_layers(pecha_opf_path, pecha_id, text_obj, old_pecha_idx):
    text_vol_span = get_text_vol_span(old_pecha_idx, text_obj.id)
    old_vols = get_old_vol(pecha_opf_path, pecha_id, text_vol_span)
    new_vols = get_new_vol(old_vols, old_pecha_idx, text_obj)
    for (vol_id, old_vol_base), (_, new_vol_base) in zip(old_vols.items(), new_vols.items()):
        updater = Blupdate(old_vol_base, new_vol_base)
        old_layers = get_old_layers(pecha_opf_path, pecha_id, vol_id)
        update_layer(pecha_opf_path, pecha_id, vol_id, old_layers, updater)

def update_other_text_index(old_pecha_idx, text_id, cur_vol_offset, vol_num):
    check_flag = False
    for text_uuid, text in old_pecha_idx['annotations'].items():
        if check_flag:
            for vol_walker, vol_span in enumerate(text['span']):
                if vol_span['vol'] == vol_num:
                    old_pecha_idx["annotations"][text_uuid]['span'][vol_walker]['start'] += cur_vol_offset
                    old_pecha_idx["annotations"][text_uuid]['span'][vol_walker]['end'] += cur_vol_offset
                elif vol_span['vol'] > vol_num:
                    return old_pecha_idx
        if text_uuid == text_id:
            check_flag = True
    return old_pecha_idx

def update_index(pecha_opf_path, pecha_id, text_obj, old_pecha_idx):
    text_vol_span = get_text_vol_span(old_pecha_idx, text_obj.id)
    old_vols = get_old_vol(pecha_opf_path, pecha_id, text_vol_span)
    new_vols = get_new_vol(old_vols, old_pecha_idx, text_obj)
    for (vol_id, old_vol_base), (_, new_vol_base) in zip(old_vols.items(), new_vols.items()):
        check_next_text = True
        vol_num = int(vol_id[1:])
        cur_vol_offset = len(new_vol_base) - len(old_vol_base)
        if cur_vol_offset != 0:
            for vol_walker, vol_span in enumerate(old_pecha_idx["annotations"][text_obj.id]['span']):
                if vol_span['vol'] == vol_num:
                    old_pecha_idx["annotations"][text_obj.id]['span'][vol_walker]['end'] += cur_vol_offset
                elif vol_span['vol'] > vol_num:
                    check_next_text = False
                    break
            if check_next_text:
                old_pecha_idx = update_other_text_index(old_pecha_idx, text_obj.id, cur_vol_offset, vol_num)
    return old_pecha_idx

def save_text(pecha_id, text_obj, **kwargs):
    pecha_opf_path = download_pecha(pecha_id, **kwargs)
    old_pecha_idx = yaml.safe_load((pecha_opf_path / f'{pecha_id}.opf/index.yml').read_text(encoding='utf-8'))
    prev_pecha_idx = copy.deepcopy(old_pecha_idx)
    new_pecha_idx = update_index(pecha_opf_path, pecha_id, text_obj, old_pecha_idx)
    update_old_layers(pecha_opf_path, pecha_id, text_obj, prev_pecha_idx)
    update_base(pecha_opf_path, pecha_id, text_obj, prev_pecha_idx)
    new_pecha_idx = yaml.safe_dump(new_pecha_idx, sort_keys=False)
    (pecha_opf_path / f'{pecha_id}.opf/index.yml').write_text(new_pecha_idx, encoding='utf-8')
    return pecha_opf_path
