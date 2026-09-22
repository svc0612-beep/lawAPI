import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import requests
import xml.etree.ElementTree as ET
from core.config import NANET_API_KEY

for key_name in ("ServiceKey", "serviceKey"):
    try:
        response = requests.get("https://apis.data.go.kr/9720000/searchservice/basic",
                                params={key_name: NANET_API_KEY, "pageno": 1, "displaylines": 1, "search": "자료명,기본권"}, timeout=20)
        print(key_name, "HTTP", response.status_code)
        try:
            root = ET.fromstring(response.text)
            print("root", root.tag)
            for node in root.iter():
                if node.tag in {"resultCode", "returnReasonCode", "returnAuthMsg", "resultMsg", "errMsg"}:
                    # Emit only bounded, code-like error values, never response body.
                    value = (node.text or "").strip()
                    if all(c.isupper() or c.isdigit() or c in "_ -" for c in value):
                        print(node.tag, value[:100])
        except ET.ParseError:
            print("non-XML response")
    except requests.RequestException:
        print(key_name, "transport error")
