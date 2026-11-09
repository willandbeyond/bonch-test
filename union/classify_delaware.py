import json, math, pathlib, urllib.parse, urllib.request
p=pathlib.Path("union/routes.geojson")
data=json.loads(p.read_text())
feature=next(f for f in data["features"] if f["properties"]["number"]==1)
coords=feature["geometry"]["coordinates"]
lats=[c[1] for c in coords]; lons=[c[0] for c in coords]
bbox=(min(lats)-.004,min(lons)-.004,max(lats)+.004,max(lons)+.004)
query=f'[out:json][timeout:90];way["highway"]["name"~"^Delaware (Avenue|Ave)",i]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});out geom;'
req=urllib.request.Request("https://overpass.kumi.systems/api/interpreter",data=urllib.parse.urlencode({"data":query}).encode(),headers={"User-Agent":"bonch-fyi-union-route-classifier/1.0"})
with urllib.request.urlopen(req,timeout=110) as response: osm=json.load(response)
ways=[[(pt["lon"],pt["lat"]) for pt in w["geometry"]] for w in osm["elements"] if w.get("geometry")]
if not ways: raise ValueError("No Delaware Avenue road geometry returned")
def distance_m(p,a,b):
    k=111320; c=math.cos(math.radians(p[1]))
    x,y=(p[0]-a[0])*k*c,(p[1]-a[1])*k
    dx,dy=(b[0]-a[0])*k*c,(b[1]-a[1])*k
    t=max(0,min(1,(x*dx+y*dy)/(dx*dx+dy*dy))) if dx*dx+dy*dy else 0
    return math.hypot(x-t*dx,y-t*dy)
roads=[(a,b) for way in ways for a,b in zip(way,way[1:])]
def near(p): return min(distance_m(p,a,b) for a,b in roads)
# Every original GPX edge is classified using its midpoint; 22m tolerates parallel sidewalks.
flags=[]
for a,b in zip(coords,coords[1:]):
    mid=((a[0]+b[0])/2,(a[1]+b[1])/2)
    flags.append(near(mid)<=22)
# Avoid isolated classifications at junctions.
for i in range(1,len(flags)-1):
    if flags[i-1]==flags[i+1]!=flags[i]:flags[i]=flags[i-1]
feature["properties"]["namedRoadEdges"]=flags
feature["properties"]["classificationMethod"]="OSM named-way proximity (22m), midpoint per GPX edge"
p.write_text(json.dumps(data,separators=(",",":")))
print("OSM ways:",len(ways),"named-road edges:",sum(flags),"connector edges:",len(flags)-sum(flags))
