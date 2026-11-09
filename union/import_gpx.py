#!/usr/bin/env python3
import json, pathlib, re, xml.etree.ElementTree as ET, zipfile
folder=pathlib.Path("downloaded")
features=[]
for file in folder.rglob("*.gpx"):
    match=re.search(r"Running the Union #([0-9]+) (.+?)\.gpx$",file.name,re.I)
    if not match: continue
    number=int(match.group(1))
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
    features.append({"type":"Feature","properties":{"number":number,"state":match.group(2),"source":"PlotARoute GPX"},"geometry":geometry})
    print(f"#{number} {match.group(2)}: {sum(map(len,segments))} points")
assert {f["properties"]["number"] for f in features}==set(range(1,18)), "Missing or duplicate route numbers"
pathlib.Path("union/routes.geojson").write_text(json.dumps({"type":"FeatureCollection","features":sorted(features,key=lambda f:f["properties"]["number"])},separators=(",",":")))
