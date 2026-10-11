"""Build a standalone, offline feature inspector. Deliberately offers no route directions."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RUN='rpi_navigation_20261011_pass04'
DIR=ROOT/'gis/cleaned'/RUN

def main():
    data={name:json.loads((DIR/(name+'.json')).read_text()) for name in ['features','landscape_review','closure_review','validation']}
    data['buildings']=json.loads((ROOT/'gis/cleaned/pilot/osm/buildings.json').read_text())['features']
    template=(ROOT/'scripts/navigation_review_template.html').read_text(encoding='utf-8')
    encoded=json.dumps(data,separators=(',',':')).replace('<','\\u003c')
    with (DIR/'index.html').open('x',encoding='utf-8',newline='\n') as f:f.write(template.replace('__DATA__',encoded))
    print(DIR/'index.html')

if __name__=='__main__':main()
