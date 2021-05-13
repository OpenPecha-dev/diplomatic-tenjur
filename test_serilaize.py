import os
from pathlib import Path

from openpecha.formatters import HFMLFormatter
from openpecha.serializers import HFMLSerializer

if __name__ == "__main__":
    opf_path = "./opfs/P000999/P000999.opf"
    hfml_path = "./hfmls/"
    serializer = HFMLSerializer(opf_path, text_id="D1346")
    serializer.serialize(output_path=hfml_path)
