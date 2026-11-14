#!/usr/bin/env python3
import json, pathlib, re, xml.etree.ElementTree as ET, zipfile
folder=pathlib.Path("downloaded")
existing=json.loads(pathlib.Path("union/routes.geojson").read_text())
features={f["properties"]["number"]:f for f in existing["features"]}
changed=[]
for file in folder.rglob("*.gpx"):
    match=re.search(r"Running the Union #([0-9]+) (.+?)\.gpx$",file.name,re.I)
    if not match: continue
    number=int(match.group(1))
    if number not in range(44,51):continue
    root=ET.parse(file).getroot()
    segments=[]
    for tag in ("trkseg","rte"):
        for seg in root.iter():
            if seg.tag.rsplit("}",1)[-1]!=tag: continue
            coords=[]
            for p in seg:
                if p.tag.rsplit("}",1)[-1] not in ("trkpt","rtept"):continue
                if "lat" in p.attrib and "lon" in p.attrib:coords.append([float(p.attrib["lon"]),float(p.attrib["lat"])])
            if len(coords)>=2:segments.append(coords)
    if not segments:raise ValueError(f"No coordinates in {file.name}")
    geometry={"type":"LineString","coordinates":segments[0]} if len(segments)==1 else {"type":"MultiLineString","coordinates":segments}
    old=features.get(number)
    if old is None:
        old={"type":"Feature","properties":{"number":number,"state":match.group(2),"source":"PlotARoute GPX"},"geometry":geometry}
        features[number]=old
        changed.append(number)
    if old["geometry"]!=geometry:
        old["geometry"]=geometry
        old["properties"].pop("namedRoadEdges",None)
        old["properties"].pop("classificationMethod",None)
        changed.append(number)
    print(f"#{number} {match.group(2)}: {sum(map(len,segments))} points")
assert set(range(1,51)).issubset(features), "Missing expected routes"
print(f"Updated GPX geometries: {changed}")
pathlib.Path("union/routes.geojson").write_text(json.dumps({"type":"FeatureCollection","features":[features[n] for n in sorted(features)]},separators=(",",":")))
