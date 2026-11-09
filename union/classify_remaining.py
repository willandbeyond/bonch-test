"""Classify remaining Running the Union traces using named OSM highway geometry."""
import json, math, pathlib, re, time, urllib.request, xml.etree.ElementTree as ET

path = pathlib.Path("union/routes.geojson")
data = json.loads(path.read_text())
failures = []

def distance_m(p, a, b):
    k = 111320
    c = math.cos(math.radians(p[1]))
    x, y = (p[0]-a[0])*k*c, (p[1]-a[1])*k
    dx, dy = (b[0]-a[0])*k*c, (b[1]-a[1])*k
    t = max(0, min(1, (x*dx+y*dy)/(dx*dx+dy*dy))) if dx*dx+dy*dy else 0
    return math.hypot(x-t*dx, y-t*dy)

for feature in data["features"]:
    props = feature["properties"]
    n = props["number"]
    if n == 1 or props.get("namedRoadEdges"):
        continue
    geom = feature["geometry"]
    if geom["type"] != "LineString":
        failures.append(f"#{n}: unsupported {geom['type']}")
        continue
    coords = geom["coordinates"]
    name = props["state"]
    stem = re.sub(r"\s+(Ave|Avenue|Dr|Drive)\.?$", "", name, flags=re.I).strip()
    # Exact road name, including both Avenue and Drive variants.
    pattern = re.compile(r"^" + re.escape(stem) + r"\s+(Avenue|Ave\.?|Drive|Dr\.?)(?:\s|$)", re.I)
    ways, seen = [], set()
    failed_chunks = 0
    print(f"CLASSIFY #{n} {name}: {len(coords)} points", flush=True)
    for i in range(0, len(coords), 20):
        chunk = coords[max(0,i-1):min(len(coords),i+21)]
        pad = .00045
        west=min(c[0] for c in chunk)-pad
        east=max(c[0] for c in chunk)+pad
        south=min(c[1] for c in chunk)-pad
        north=max(c[1] for c in chunk)+pad
        # OSM API rejects bounding boxes whose area exceeds 0.25 square degrees
        # and some high-density urban blocks exceed its node limit.
        url=f"https://api.openstreetmap.org/api/0.6/map?bbox={west},{south},{east},{north}"
        try:
            req=urllib.request.Request(url,headers={"User-Agent":"bonch-fyi-route-classifier/1.0 (route visualization)"})
            for attempt in range(4):
                try:
                    with urllib.request.urlopen(req,timeout=45) as response:
                        root=ET.parse(response).getroot()
                    break
                except urllib.error.HTTPError as exc:
                    if exc.code != 429 or attempt == 3:
                        raise
                    delay = 15 * (attempt+1)
                    print(f"  Rate limited; waiting {delay}s",flush=True)
                    time.sleep(delay)
            nodes={node.attrib["id"]:(float(node.attrib["lon"]),float(node.attrib["lat"])) for node in root.findall("node")}
            for way in root.findall("way"):
                wid=way.attrib["id"]
                if wid in seen: continue
                tags={tag.attrib["k"]:tag.attrib["v"] for tag in way.findall("tag")}
                if "highway" not in tags or not pattern.search(tags.get("name","")): continue
                pts=[nodes[nd.attrib["ref"]] for nd in way.findall("nd") if nd.attrib["ref"] in nodes]
                if len(pts)>1:
                    ways.append(pts)
                    seen.add(wid)
        except Exception as exc:
            failed_chunks += 1
            print(f"  chunk {i//20+1} failed: {exc!r}",flush=True)
        time.sleep(2.5)
    if not ways or failed_chunks:
        failures.append(f"#{n} {name}: {len(ways)} ways, {failed_chunks} failed chunks")
        print("  SKIPPED: incomplete OSM coverage",flush=True)
        continue
    roads=[(a,b) for way in ways for a,b in zip(way,way[1:])]
    flags=[]
    for a,b in zip(coords,coords[1:]):
        mid=((a[0]+b[0])/2,(a[1]+b[1])/2)
        flags.append(min(distance_m(mid,u,v) for u,v in roads)<=22)
    for i in range(1,len(flags)-1):
        if flags[i-1]==flags[i+1]!=flags[i]:
            flags[i]=flags[i-1]
    props["namedRoadEdges"]=flags
    props["classificationMethod"]="OSM primary map API named-way proximity (22m)"
    print(f"  DONE: {sum(flags)} named-road edges, {len(flags)-sum(flags)} connector edges",flush=True)
    path.write_text(json.dumps(data,separators=(",",":")))

print("FAILED:",failures,flush=True)
if failures:
    raise RuntimeError("; ".join(failures))
