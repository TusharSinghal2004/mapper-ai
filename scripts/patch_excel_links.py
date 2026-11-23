"""Add native hyperlinks, a capability missing from the bundled sheet renderer.

All workbook data and formatting are authored by Artifact Tool; this narrow
OpenXML pass adds only source and sheet-navigation hyperlink elements.
"""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
import json
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
MAIN='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
REL='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
PKG='http://schemas.openxmlformats.org/package/2006/relationships'
ET.register_namespace('',MAIN)
ET.register_namespace('r',REL)

def main():
    apps=json.loads((ROOT/'dist/apps.json').read_text(encoding='utf-8'))
    target=ROOT/'dist/integration-atlas.xlsx'
    with ZipFile(target) as z:files={name:z.read(name) for name in z.namelist()}
    sheets=[ET.fromstring(files[f'xl/worksheets/sheet{i}.xml']) for i in (1,2)]
    links=[ET.Element(f'{{{MAIN}}}hyperlinks') for _ in sheets]
    relpath='xl/worksheets/_rels/sheet2.xml.rels'
    relationships=ET.fromstring(files[relpath]) if relpath in files else ET.Element(f'{{{PKG}}}Relationships')
    current=5;external=0
    for index,app in enumerate(apps):
        ET.SubElement(links[0],f'{{{MAIN}}}hyperlink',{'ref':f'K{index+5}','location':f"'Evidence'!A{current}"})
        for url in app['sources'] or [None]:
            if url:
                external+=1
                rid=f'rIdAtlasSource{external}'
                ET.SubElement(links[1],f'{{{MAIN}}}hyperlink',{'ref':f'D{current}',f'{{{REL}}}id':rid})
                ET.SubElement(relationships,f'{{{PKG}}}Relationship',{'Id':rid,'Type':REL+'/hyperlink','Target':url,'TargetMode':'External'})
            ET.SubElement(links[1],f'{{{MAIN}}}hyperlink',{'ref':f'E{current}','location':f"'App research'!A{index+5}"})
            current+=1
    for i,root in enumerate(sheets):
        # SpreadsheetML order places hyperlinks before print/page/drawing/table parts.
        after={'printOptions','pageMargins','pageSetup','headerFooter','rowBreaks','colBreaks','customProperties','cellWatches','ignoredErrors','smartTags','drawing','legacyDrawing','legacyDrawingHF','picture','oleObjects','controls','webPublishItems','tableParts','extLst'}
        position=next((j for j,child in enumerate(root) if child.tag.split('}')[-1] in after),len(root))
        root.insert(position,links[i])
        files[f'xl/worksheets/sheet{i+1}.xml']=ET.tostring(root,encoding='utf-8',xml_declaration=True)
    files[relpath]=ET.tostring(relationships,encoding='utf-8',xml_declaration=True)
    temporary=target.with_suffix('.tmp')
    with ZipFile(temporary,'w',ZIP_DEFLATED) as z:
        for name,data in files.items():z.writestr(name,data)
    temporary.replace(target)
    print(f'Added {external} clickable source URLs and 327 internal navigation links.')

if __name__=='__main__':main()
