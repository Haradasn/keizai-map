"""都道府県の境界(地球地図日本・dataofjapan/land の japan.geojson)を間引いて site/vendor/japan-pref.json にする(一度だけ実行。結果をコミット)。
使い方: python3 scripts/build_geo.py /path/to/japan.geojson
出典: 地球地図日本(国土地理院)。非営利での利用、出典の明記が条件。"""
import json,sys,pathlib
from shapely.geometry import shape,mapping
src=json.load(open(sys.argv[1],encoding="utf-8")); out=[]
for f in src["features"]:
    g=shape(f["geometry"]).simplify(0.012,preserve_topology=True)
    parts=[g] if g.geom_type=="Polygon" else list(g.geoms)
    parts=[p for p in parts if p.area>0.015]                       # 小さな島は落とす
    from shapely.geometry import MultiPolygon
    m=mapping(MultiPolygon(parts))
    rnd=lambda c:[round(c[0],3),round(c[1],3)]
    m["coordinates"]=[[[rnd(c) for c in ring] for ring in poly] for poly in m["coordinates"]]
    out.append({"type":"Feature","properties":{"id":f["properties"]["id"],"name":f["properties"]["nam_ja"]},"geometry":m})
p=pathlib.Path(__file__).resolve().parent.parent/"site/vendor/japan-pref.json"
p.write_text(json.dumps({"type":"FeatureCollection","features":out},ensure_ascii=False,separators=(",",":")),encoding="utf-8"); print(p.stat().st_size,"bytes")
