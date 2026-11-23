"""Build the website's Excel-compatible full-data download from its JSON source."""
import csv
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FIELDS=[('id','App ID'),('name','App'),('category','Category'),('description','What it does'),('auth','Auth methods'),('access','Access route'),('accessNote','Access requirements'),('api','API surface'),('mcp','Existing MCP'),('verdict','Buildability verdict'),('blocker','Main blocker or condition'),('sources','Evidence URLs'),('evidenceNotes','Evidence notes'),('confidence','Research confidence'),('checkedAt','Date checked'),('verification','Verification status')]

def main():
    rows=json.loads((ROOT/'dist/apps.json').read_text(encoding='utf-8'))
    # UTF-8 BOM preserves non-ASCII names when opening directly in Excel.
    with (ROOT/'dist/apps.csv').open('w',encoding='utf-8-sig',newline='') as output:
        writer=csv.writer(output)
        writer.writerow([label for _,label in FIELDS])
        for row in rows:
            values=[]
            for field,_ in FIELDS:
                value=row.get(field,'')
                if isinstance(value,list):value=('\n' if field=='sources' else '; ').join(value)
                if field=='sources' and not value:value='No official source established; follow-up required'
                # Keep documentation text as data when opened in a spreadsheet.
                if isinstance(value,str) and value.lstrip().startswith(('=','+','-','@')):value="'"+value
                values.append(value)
            writer.writerow(values)
    print(f'Exported {len(rows)} apps with {len(FIELDS)} columns to dist/apps.csv.')

if __name__=='__main__':main()
