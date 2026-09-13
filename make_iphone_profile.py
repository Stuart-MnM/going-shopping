import base64
import re
import plistlib
from pathlib import Path

LOCAL_APPDATA = Path.home() / "AppData" / "Local"

root_ca = LOCAL_APPDATA / "mkcert" / "rootCA.pem"
output = Path.home() / "Desktop" / "GoingShopping-mkcert.mobileconfig"

pem_text = root_ca.read_text(encoding="ascii")

match = re.search(
    r"-----BEGIN CERTIFICATE-----(.*?)-----END CERTIFICATE-----",
    pem_text,
    re.DOTALL,
)

if not match:
    raise RuntimeError("Could not find certificate in rootCA.pem")

der_bytes = base64.b64decode(
    "".join(match.group(1).split())
)

profile = {
    "PayloadContent": [
        {
            "PayloadCertificateFileName": "rootCA.pem",
            "PayloadContent": base64.b64encode(der_bytes),
            "PayloadDescription": "Trust certificate for GoingShopping on the local network",
            "PayloadDisplayName": "GoingShopping Local Certificate",
            "PayloadIdentifier": "local.goingshopping.mkcert.root",
            "PayloadOrganization": "GoingShopping",
            "PayloadType": "com.apple.security.root",
            "PayloadUUID": "6D5D0E4E-7F8B-4C8C-9A4B-2D3A9E2A1F01",
            "PayloadVersion": 1,
        }
    ],
    "PayloadDisplayName": "GoingShopping Certificate",
    "PayloadIdentifier": "local.goingshopping.profile",
    "PayloadOrganization": "GoingShopping",
    "PayloadRemovalDisallowed": False,
    "PayloadType": "Configuration",
    "PayloadUUID": "B27D1DB4-2E9F-4C5B-9C6F-9A7A5E3E2D01",
    "PayloadVersion": 1,
}

with output.open("wb") as file:
    plistlib.dump(profile, file, fmt=plistlib.FMT_XML)

print(f"Created: {output}")