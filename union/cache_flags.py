#!/usr/bin/env python3
"""Cache the 50 US state flag PNGs locally for Running the Union."""
import json
import pathlib
import time
import urllib.error
import urllib.parse
import urllib.request

STATES = """Delaware|Pennsylvania|New Jersey|Georgia|Connecticut|Massachusetts|Maryland|South Carolina|New Hampshire|Virginia|New York|North Carolina|Rhode Island|Vermont|Kentucky|Tennessee|Ohio|Louisiana|Indiana|Mississippi|Illinois|Alabama|Maine|Missouri|Arkansas|Michigan|Florida|Texas|Iowa|Wisconsin|California|Minnesota|Oregon|Kansas|West Virginia|Nevada|Nebraska|Colorado|North Dakota|South Dakota|Montana|Washington|Idaho|Wyoming|Utah|Oklahoma|New Mexico|Arizona|Alaska|Hawaii""".split("|")
OUT = pathlib.Path(__file__).parent / "flags"
OUT.mkdir(exist_ok=True)
HEADERS = {"User-Agent": "RunningTheUnion/1.0 (static flag cache for personal running map)"}

def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=45) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            if error.code != 429 or attempt == 5:
                raise
            wait = min(90, 15 * (attempt + 1))
            print(f'Rate limited; waiting {wait}s before retry', flush=True)
            time.sleep(wait)

def image_url(state):
    filename = state.lower().replace(" ", "_") + ".png"
    return ("https://raw.githubusercontent.com/stevenrskelton/flag-icon/master/png/225/us/" + filename,
            "stevenrskelton/flag-icon: png/225/us/" + filename)

manifest = {}
failures = []
for index, state in enumerate(STATES, 1):
    destination = OUT / f"{index:02d}.png"
    try:
        if not destination.exists():
            url, attribution = image_url(state)
            content = fetch(url)
            if b"<svg" not in content[:5000]:
                raise ValueError("Downloaded content is not an SVG")
            destination.write_bytes(content)
            time.sleep(0.1)
        else:
            attribution = f"Flag of {state} (stevenrskelton/flag-icon)"
        manifest[str(index)] = {"state": state, "file": f"flags/{index:02d}.png", "source": "stevenrskelton/flag-icon (GitHub)", "title": attribution}
        print(f"{index:02d} {state}: cached")
    except Exception as error:
        failures.append(f"{state}: {error}")
        print(f"{index:02d} {state}: ERROR {error}", flush=True)
(OUT / "sources.json").write_text(json.dumps(manifest, indent=2) + "\n")
if failures:
    raise SystemExit("Flag download failed: " + "; ".join(failures))
