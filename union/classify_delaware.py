import json, math, pathlib, urllib.parse, urllib.request
p=pathlib.Path("union/routes.geojson")
data=json.loads(p.read_text())
feature=next(f for f in data["features"] if f["properties"]["number"]==1)
coords=feature["geometry"]["coordinates"]
lats=[c[1] for c in coords]; lons=[c[0] for c in coords]
bbox=(min(lats)-.004,min(lons)-.004,max(lats)+.004,max(lons)+.004)
query=f'[out:json][timeout:90];way["highway"]["name"~"^Delaware (Avenue|Ave)",i]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});out geom;'
# Fetch named ways from the primary OSM API in narrow bounding boxes.
# This avoids Overpass servers entirely.
import xml.etree.ElementTree as ET
ways=[]
seen=set()
# Small overlapping bounding boxes avoid the OSM API's maximum-node limit.
import re, time
for i in range(0,len(coords),8):
    chunk=coords[max(0,i-1):min(len(coords),i+9)]
    pad=.00045
    west=min(c[0] for c in chunk)-pad
    east=max(c[0] for c in chunk)+pad
    south=min(c[1] for c in chunk)-pad
    north=max(c[1] for c in chunk)+pad
    url=f"https://api.openstreetmap.org/api/0.6/map?bbox={west},{south},{east},{north}"
    print(f"OSM chunk {i//8+1}: {west:.5f},{south:.5f},{east:.5f},{north:.5f}",flush=True)
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"bonch-fyi-route-classifier/1.0 (route visualization)"}),timeout=45) as response:
            root=ET.parse(response).getroot()
    except Exception as exc:
        print("Chunk failed",repr(exc),flush=True)
        continue
    nodes={n.attrib["id"]:(float(n.attrib["lon"]),float(n.attrib["lat"])) for n in root.findall("node")}
    for w in root.findall("way"):
        wid=w.attrib["id"]
        if wid in seen:continue
        tags={t.attrib["k"]:t.attrib["v"] for t in w.findall("tag")}
        if "highway" not in tags or not re.search(r"^Delaware (Avenue|Ave)",tags.get("name",""),re.I):continue
        pts=[nodes[n.attrib["ref"]] for n in w.findall("nd") if n.attrib["ref"] in nodes]
        if len(pts)>1:
            ways.append(pts)
            seen.add(wid)
    time.sleep(.3)
if not ways:raise ValueError("OSM map API returned no Delaware Avenue road geometry")
def distance_m(p,a,b):
    k=111320; c=math.cos(math.radians(p[1]))
    x,y=(p[0]-a[0])*k*c,(p[1]-a[1])*k
    dx,dy=(b[0]-a[0])*k*c,(b[1]-a[1])*k
    t=max(0,min(1,(x*dx+y*dy)/(dx*dx+dy*dy))) if dx*dx+dy*dy else 0
    return math.hypot(x-t*dx,y-t*dy)
roads=[(a,b) for way in ways for a,b in zip(way,way[1:])]
def near(p): return min(distance_m(p,a,b) for a,b in roads)
flags=[]
for a,b in zip(coords,coords[1:]):
    mid=((a[0]+b[0])/2,(a[1]+b[1])/2)
    flags.append(near(mid)<=22)
for i in range(1,len(flags)-1):
    if flags[i-1]==flags[i+1]!=flags[i]:flags[i]=flags[i-1]
feature["properties"]["namedRoadEdges"]=flags
feature["properties"]["classificationMethod"]="OSM primary map API named-way proximity (22m)"
p.write_text(json.dumps(data,separators=(",",":")))
print("OSM ways:",len(ways),"named-road edges:",sum(flags),"connector edges:",len(flags)-sum(flags))
