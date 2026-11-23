import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {Workbook, SpreadsheetFile} from '@oai/artifact-tool';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const apps=JSON.parse(await fs.readFile(path.join(root,'dist/apps.json'),'utf8'));
const workbook=Workbook.create();
const sheet=workbook.worksheets.add('App research');
const evidence=workbook.worksheets.add('Evidence');
const verdicts={buildable:'Looks ready to build',conditional:'Possible, with conditions',unknown:'Not yet clear',local:'Runs on your computer'};
const access={'self-serve':'Sign up yourself',trial:'Trial available',paid:'Paid account needed',gated:'Approval or special access',unknown:'Not yet clear'};
const headers=['App','Category','Auth methods','Access route','Buildability','What it does','Access requirements','API surface','Existing MCP','Main blocker or condition','Evidence','Confidence','Date checked','Research notes','Verification status','App ID'];
const widths=[22,25,32,24,30,48,60,60,46,54,22,14,15,60,52,9];
const letters='ABCDEFGHIJKLMNOP'.split('');
const firstSource=new Map();
const sourceRows=[];
for(const [i,app] of apps.entries()){
  firstSource.set(app.id,sourceRows.length+5);
  if(app.sources.length) app.sources.forEach((url,j)=>sourceRows.push([app.id,app.name,j+1,url,i+5]));
  else sourceRows.push([app.id,app.name,null,'No official source established. Follow-up required.',i+5]);
}
const values=apps.map(app=>[app.name,app.category,app.auth.join('; '),access[app.access]||app.access,verdicts[app.verdict]||app.verdict,app.description,app.accessNote,app.api,app.mcp,app.blocker,'',app.confidence,new Date((app.checkedAt||'2026-11-23')+'T00:00:00Z'),app.evidenceNotes,app.verification,app.id]);

function base(ws,lastCol,lastRow,title,context){
  ws.showGridLines=false;
  const all=ws.getRange(`A1:${lastCol}${lastRow}`);
  all.format.font={name:'Arial',size:11,color:'#192E31'};
  all.format.verticalAlignment='top';
  ws.getRange(`A1:${lastCol}1`).format.rowHeight=12;
  ws.getRange('A2').values=[[title]];
  ws.getRange('A2').format.font={name:'Arial',size:17,bold:true,color:'#142C4B'};
  ws.getRange(`A2:${lastCol}2`).format.rowHeight=30;
  ws.getRange('A3').values=[[context]];
  ws.getRange('A3').format.font={name:'Arial',size:11,color:'#526468'};
  ws.getRange(`A3:${lastCol}3`).format.rowHeight=26;
  ws.freezePanes.freezeRows(4);
  ws.freezePanes.freezeColumns(ws===sheet?1:2);
  ws.tabColor='#142C4B';
}
base(sheet,'P',104,'Integration Atlas — 100 apps','Use the filters to compare apps. Documentation assessment; human audit and vendor sign-in tests are pending.');
sheet.getRange('A4:P4').values=[headers];
sheet.getRange('A5:P104').values=values;
const table=sheet.tables.add('A4:P104',true,'AppResearch');
table.showFilterButton=true;
table.style='TableStyleMedium2';
sheet.getRange('A4:P104').format.wrapText=true;
sheet.getRange('A4:P4').format={fill:'#142C4B',font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},rowHeight:36,horizontalAlignment:'center',verticalAlignment:'center',wrapText:true};
for(let i=0;i<widths.length;i++)sheet.getRange(`${letters[i]}4:${letters[i]}104`).format.columnWidth=widths[i];
sheet.getRange('M5:M104').setNumberFormat('yyyy-mm-dd');
sheet.getRange('P5:P104').setNumberFormat('0');
const quote=s=>String(s).replaceAll('"','""');
for(const [i,app] of apps.entries()){
  const row=i+5;
  const range=sheet.getRange(`A${row}:P${row}`);
  range.format.fill=i%2?'#F1F5FA':'#FFFFFF';
  // Fit prose without importing the oversized heights from a CSV opened in Excel.
  let lines=1;
  values[i].forEach((value,col)=>{
    if(value instanceof Date||typeof value!=='string')return;
    const available=Math.max(8,Math.floor(widths[col]*.88));
    lines=Math.max(lines,...value.split('\n').map(p=>Math.max(1,Math.ceil(p.length/available))));
  });
  range.format.rowHeight=Math.max(60,lines*16+14);
  sheet.getRange(`A${row}`).format.font={bold:true,color:'#142C4B'};
  sheet.getRange(`K${row}`).values=[[app.sources.length?app.sources.length+' source'+(app.sources.length===1?'':'s'):'Evidence missing']];
  sheet.getRange(`K${row}`).format.font={color:'#007968'};
}
const decisions=sheet.getRange('E5:E104');
for(const [label,fill,color] of [['Looks ready to build','#E0F1E9','#075B48'],['Possible, with conditions','#FFF0CF','#795700'],['Not yet clear','#FBE4E5','#8C2633'],['Runs on your computer','#E6EDFA','#244F89']]){
  decisions.conditionalFormats.add('containsText',{text:label,format:{fill,font:{color,bold:true}}});
}

const end=sourceRows.length+4;
base(evidence,'E',end,'Evidence — original documentation','Each source belongs to an app. Use “Back to app” to return to the complete research record.');
evidence.tabColor='#007968';
evidence.getRange('A4:E4').values=[['App ID','App','Source number','Documentation URL','Research record']];
evidence.getRange(`A5:E${end}`).values=sourceRows;
const sources=evidence.tables.add(`A4:E${end}`,true,'AppEvidence');
sources.showFilterButton=true;
sources.style='TableStyleMedium2';
evidence.getRange(`A4:E${end}`).format.wrapText=true;
evidence.getRange('A4:E4').format={fill:'#142C4B',font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},rowHeight:36,horizontalAlignment:'center',verticalAlignment:'center',wrapText:true};
for(const [col,width] of [['A',9],['B',25],['C',15],['D',105],['E',22]])evidence.getRange(`${col}4:${col}${end}`).format.columnWidth=width;
for(const [i,source] of sourceRows.entries()){
  const row=i+5;
  const range=evidence.getRange(`A${row}:E${row}`);
  range.format.fill=i%2?'#F1F5FA':'#FFFFFF';
  range.format.rowHeight=Math.max(40,Math.ceil(source[3].length/90)*16+14);
  if(source[3].startsWith('https://')){
    evidence.getRange(`D${row}`).format.font={color:'#007968'};
  }
  evidence.getRange(`E${row}`).values=[['Back to app']];
  evidence.getRange(`E${row}`).format.font={color:'#007968'};
}
workbook.recalculate();
console.log((await workbook.inspect({kind:'table',range:"'App research'!A4:E7",include:'values',tableMaxRows:4,tableMaxCols:5,maxChars:2000})).ndjson);
const errors=await workbook.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#NULL!',options:{useRegex:true,maxResults:15},maxChars:1500});
console.log(errors.ndjson);
await fs.mkdir(path.join(root,'.qa'),{recursive:true});
for(const [name,range,file] of [['App research','A1:F8','excel-apps-preview.png'],['Evidence','A1:E9','excel-evidence-preview.png']]){
  const preview=await workbook.render({sheetName:name,range,scale:1.5,format:'png'});
  await fs.writeFile(path.join(root,'.qa',file),new Uint8Array(await preview.arrayBuffer()));
}
const file=await SpreadsheetFile.exportXlsx(workbook);
await file.save(path.join(root,'dist/integration-atlas.xlsx'));
// The bundled renderer does not implement HYPERLINK formulas. Add native
// Excel hyperlinks after export, keeping plain display text and no formulas.
const python=process.platform==='win32'?path.join(root,'.venv/Scripts/python.exe'):'python3';
console.log(execFileSync(python,[path.join(root,'scripts/patch_excel_links.py')],{encoding:'utf8',cwd:root}).trim());
console.log(JSON.stringify({apps:apps.length,evidenceRows:sourceRows.length,output:'dist/integration-atlas.xlsx'}));
