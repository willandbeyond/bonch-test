#!/usr/bin/env python3
"""Cache the 50 US state flag SVGs locally for Running the Union."""
import json
import pathlib
import time
import urllib.parse
import urllib.request

STATES = """Delaware|Pennsylvania|New Jersey|Georgia|Connecticut|Massachusetts|Maryland|South Carolina|New Hampshire|Virginia|New York|North Carolina|Rhode Island|Vermont|Kentucky|Tennessee|Ohio|Louisiana|Indiana|Mississippi|Illinois|Alabama|Maine|Missouri|Arkansas|Michigan|Florida|Texas|Iowa|Wisconsin|California|Minnesota|Oregon|Kansas|West Virginia|Nevada|Nebraska|Colorado|North Dakota|South Dakota|Montana|Washington|Idaho|Wyoming|Utah|Oklahoma|New Mexico|Arizona|Alaska|Hawaii""".split("|")
OUT = pathlib.Path(__file__).parent / "flags"
OUT.mkdir(exist_ok=True)
HEADERS = {"User-Agent": "RunningTheUnion/1.0 (static flag cache for personal running map; Wikimedia Commons attribution)"}

def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=45) as response:
        return response.read()

def image_url(state):
    names = [f"Flag of {state}.svg"]
    if state == "Georgia":
        names.insert(0, "Flag of Georgia (U.S. state).svg")
    for name in names:
        params = urllib.parse.urlencode({"action":"query","format":"json","titles":"File:"+name,"prop":"imageinfo","iiprop":"url"})
        data = json.loads(fetch("https://commons.wikimedia.org/w/api.php?"+params))
        for page in data["query"]["pages"].values():
            info = page.get("imageinfo")
            if info:
                return info[0]["url"], page["title"]
    raise RuntimeError(f"No Commons SVG found for {state}")

manifest = {}
failures = []
for index, state in enumerate(STATES, 1):
    destination = OUT / f"{index:02d}.svg"
    try:
        if not destination.exists():
            url, attribution = image_url(state)
            content = fetch(url)
            if b"<svg" not in content[:5000]:
                raise ValueError("Downloaded content is not an SVG")
            destination.write_bytes(content)
            time.sleep(0.15)
        else:
            attribution = f"Flag of {state} (Wikimedia Commons)"
        manifest[str(index)] = {"state": state, "file": f"flags/{index:02d}.svg", "source": "Wikimedia Commons", "title": attribution}
        print(f"{index:02d} {state}: cached")
    except Exception as error:
        failures.append(f"{state}: {error}")
        print(f"{index:02d} {state}: ERROR {error}", flush=True)
(OUT / "sources.json").write_text(json.dumps(manifest, indent=2) + "\n")
if failures:
    raise SystemExit("Flag download failed: " + "; ".join(failures))
