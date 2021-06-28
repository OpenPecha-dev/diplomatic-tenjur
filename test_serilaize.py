import os
from pathlib import Path

from openpecha.formatters import HFMLFormatter
from openpecha.serializers import HFMLSerializer

if __name__ == "__main__":
    hfml_path = "./"
    opfs_path = "./opf/"
    hfml_text = "./P000888/"
    pecha_id = "P000888"
    opf_path = f"./opf/{pecha_id}/{pecha_id}.opf"
    # formatter = HFMLFormatter(output_path=opfs_path)
    # formatter.create_opf(hfml_text, pecha_id)
    serializer = HFMLSerializer(opf_path, text_id="D1119")
    serializer.serialize(output_path=hfml_path)
