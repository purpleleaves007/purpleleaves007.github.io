#!/usr/bin/env python3
"""Update journal JIFs from public publisher files; keep verified records on source failures."""
import argparse
from datetime import datetime, timezone
from html.parser import HTMLParser
import io
import json
import math
import os
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.parse import urljoin, urlsplit
import xml.etree.ElementTree as ET
from zipfile import ZipFile

IEEE_INDEX='https://open.ieee.org/publishing-options/ieee-title-list/'
NS={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
# Exact publisher acronyms prevent title similarity from matching the wrong journal.
IEEE_IDS={
 'IEEE JSAC':'J-SAC','IEEE TDSC':'T-DSC','IEEE TCCN':'T-CCN',
 'IEEE TAFFC':'T-AFFC','IEEE THMS':'T-HMS','IEEE IoT-J':'J-IOT',
 'IEEE TIFS':'T-IFS','IEEE TMC':'T-MC','IEEE TCSVT':'T-CSVT',
 'IEEE TIM':'T-IM','IEEE TCSS':'T-CSS','IEEE CIM':'M-CI',
}
ACM_TITLES={
 'ACM IMWUT / UbiComp':'Proceedings of the ACM on Interactive, Mobile, Wearable and Ubiquitous Technologies',
 'ACM TOSN':'ACM Transactions on Sensor Networks',
}


def fetch(url):
    host=urlsplit(url).hostname or ''
    if not (host=='open.ieee.org' or host in ['www.acm.org','acm.org','www.letpub.com.cn','letpub.com.cn']):
        raise ValueError('Unexpected publisher source host')
    result=subprocess.run(['curl','--fail','--location','--silent','--show-error','--max-time','45',url],capture_output=True,check=False)
    if result.returncode:
        raise RuntimeError(f'{host} request failed (curl status {result.returncode})')
    if len(result.stdout)>20_000_000:
        raise ValueError('Unexpectedly large publisher response')
    return result.stdout


def xlsx_rows(data):
    with ZipFile(io.BytesIO(data)) as z:
        if sum(info.file_size for info in z.infolist())>50_000_000:
            raise ValueError('Unexpectedly large uncompressed workbook')
        shared=[]
        if 'xl/sharedStrings.xml' in z.namelist():
            shared=[''.join(node.itertext()) for node in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si',NS)]
        rows=[]
        for sheet in sorted(name for name in z.namelist() if re.fullmatch(r'xl/worksheets/sheet\d+\.xml',name)):
            for node in ET.fromstring(z.read(sheet)).findall('.//m:row',NS):
                row={}
                for cell in node.findall('m:c',NS):
                    col=re.sub(r'\d','',cell.attrib['r'])
                    value=cell.find('m:v',NS)
                    if cell.attrib.get('t')=='inlineStr':text=''.join(cell.find('m:is',NS).itertext())
                    elif value is None:continue
                    elif cell.attrib.get('t')=='s':text=shared[int(value.text)]
                    else:text=value.text or ''
                    row[col]=text.strip()
                if row:rows.append(row)
        return rows


def extract_ieee(data, source_url, required_year):
    rows=xlsx_rows(data)
    text=' '.join(str(v) for row in rows for v in row.values())
    # Use the metric year declared in the workbook, never the download filename year.
    year=re.search(r'Data based on the\s+(20\d{2})\s+Journal Citation Reports',text,re.I)
    if not year:raise ValueError('IEEE workbook does not explicitly identify its JIF year')
    metric_year=int(year.group(1))
    if metric_year!=required_year:raise ValueError(f'IEEE metric year is {metric_year}, expected {required_year}')
    header=next((row for row in rows if any('Journal Impact Factor' in v and '5-Year' not in v for v in row.values())),None)
    if not header:raise ValueError('IEEE JIF header missing')
    column=lambda text: next(k for k,v in header.items() if text in v)
    acro=column('Publication Acronym');jifcol=column('Journal Impact Factor');titlecol=column('Publication Title')
    quartcol=column('Quartile (JIF)')
    by_acronym={}
    for row in rows:
        if row.get(acro) in IEEE_IDS.values():
            key=row[acro]
            if key in by_acronym and any(by_acronym[key].get(col)!=row.get(col) for col in [jifcol,quartcol,titlecol]):raise ValueError(f'Conflicting IEEE journal rows: {key}')
            by_acronym[key]=row
    found={}
    for short,acronym in IEEE_IDS.items():
        if acronym not in by_acronym:raise ValueError(f'IEEE target journal not found: {short} ({acronym})')
        row=by_acronym[acronym]
        try:value=float(row[jifcol])
        except (KeyError,ValueError):raise ValueError(f'Invalid JIF for {short}')
        if not math.isfinite(value) or value<0:raise ValueError(f'Invalid JIF for {short}')
        quartile=row.get(quartcol,'')
        if not re.fullmatch(r'Q[1-4]',quartile):raise ValueError(f'Invalid quartile for {short}')
        found[short]={'jif':value,'metric_year':metric_year,'quartile':quartile,'source_url':source_url,'publisher':'IEEE','title':row.get(titlecol,short)}
    return found


class Text(HTMLParser):
    def __init__(self):super().__init__();self.parts=[];self.ignored=0
    def handle_starttag(self,tag,attrs):
        if tag in ['script','style']:self.ignored+=1
    def handle_endtag(self,tag):
        if tag in ['script','style'] and self.ignored:self.ignored-=1
    def handle_data(self,data):
        if not self.ignored:self.parts.append(data)


def extract_acm(document, source_url, required_year):
    parser=Text();parser.feed(document)
    text=re.sub(r'\s+',' ',' '.join(parser.parts))
    release_year=required_year+1
    # The release must explicitly contain a dated ACM announcement for that year.
    if not re.search(r'(?:June|July)\s+\d{1,2},?\s+'+str(release_year)+r'\b',text):
        raise ValueError('ACM release date could not be confirmed')
    if 'Journal Citation Reports' not in text:raise ValueError('ACM JCR announcement not found')
    records={}
    for short,title in ACM_TITLES.items():
        # Match a named title, then an explicit impact-factor number (not a percent increase).
        pos=text.find(title)
        if pos<0:continue
        window=text[pos+len(title):pos+len(title)+250]
        next_title=re.search(r'(?:ACM [A-Z]|Proceedings of the ACM|Communications of the ACM)',window)
        if next_title:window=window[:next_title.start()]
        match=re.search(r'(?:impact factor(?:\s+of)?|increase\s+to|\bto|\bat)\s+(\d+\.\d+)\b',window,re.I)
        if not match:continue
        value=float(match.group(1))
        if not 0<=value<1000:continue
        records[short]={'jif':value,'metric_year':required_year,'source_url':source_url,'publisher':'ACM','title':title}
    if not records:raise ValueError('ACM announcement did not contain a verified target JIF')
    return records


LETPUB_JOURNALS={
 'ACM TOSN':{'issn':'1550-4859','journal_id':'40'},
 'ACM IMWUT / UbiComp':{'issn':'2474-9567','journal_id':'39813'},
}

def extract_letpub(document, short, source_url, required_year):
    target=LETPUB_JOURNALS[short]
    # Only a publicly visible results table is read. Login-only detail values,
    # dynamic predictions and five-year IFs are never used.
    if not re.search(str(required_year+1)+r'年\s*(?:6|7|8|9)月最新影响因子数据已更新',document):
        raise ValueError('LetPub annual data-update year could not be confirmed')
    candidates=[]
    for marker in re.finditer(r'(?<![A-Za-z])IF:\s*',document):
        start=document.rfind('<tr',0,marker.start())
        end=document.find('</tr>',marker.end())
        if start<0 or end<0:continue
        row=document[start:end+5]
        ids=set(re.findall(r'journalid=(\d+)',row))
        if ids!={target['journal_id']}:continue
        parser=Text();parser.feed(row)
        text=re.sub(r'\s+',' ',' '.join(parser.parts))
        if target['issn'] not in text:continue
        if '实时影响因子' in text or '五年IF' in text:continue
        values=re.findall(r'(?<![A-Za-z])IF:\s*(\d+(?:\.\d+)?)\b',text)
        if len(values)!=1:continue
        value=float(values[0])
        if not 0<=value<1000:continue
        candidates.append(value)
    if not candidates or len(set(candidates))!=1:
        raise ValueError('No unambiguous public LetPub JIF for the exact ISSN and journal ID')
    return {'jif':candidates[0],'metric_year':required_year,'source_url':source_url,'publisher':'ACM','source_kind':'secondary','title':ACM_TITLES[short]}


def merge_metrics(previous, incoming):
    merged=dict(previous)
    for short,record in incoming.items():
        old=merged.get(short)
        if old and old['metric_year']>record['metric_year']:continue
        merged[short]=record
    return merged


def atomic_json(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile('w',dir=path.parent,suffix='.tmp',delete=False,encoding='utf-8') as temp:
        json.dump(data,temp,ensure_ascii=False,indent=2);temp.write('\n');temp_path=Path(temp.name)
    os.replace(temp_path,path)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('results/journal_metrics.json'))
    parser.add_argument('--seed',type=Path,default=Path('assets/journal-metrics.json'))
    parser.add_argument('--metric-year',type=int)
    parser.add_argument('--ieee-file',type=Path,help='Use a downloaded publisher workbook for verification')
    args=parser.parse_args()
    now=datetime.now(timezone.utc)
    required_year=args.metric_year or now.year-1
    if not 2000<=required_year<=now.year-1:raise ValueError('Invalid JIF metric year')
    previous={}
    for path in [args.seed,args.output]:
        if path.exists():previous=merge_metrics(previous,json.loads(path.read_text()).get('journals',{}))
    sources={};fresh={};warnings=[]
    try:
        if args.ieee_file:
            content=args.ieee_file.read_bytes();url='https://open.ieee.org/wp-content/uploads/IEEE-Title-List-September-2026.xlsx'
        else:
            index=fetch(IEEE_INDEX).decode('utf-8')
            urls=re.findall(r'href=[\"\']([^\"\']+\.xlsx(?:\?[^\"\']*)?)[\"\']',index,re.I)
            candidates=[urljoin(IEEE_INDEX,u) for u in urls if 'title-list' in u.lower()]
            if not candidates:raise ValueError('IEEE workbook download link not found')
            url=candidates[0];content=fetch(url)
        records=extract_ieee(content,url,required_year);fresh.update(records)
        sources['IEEE']={'status':'updated','metric_year':required_year,'count':len(records),'url':url}
    except Exception as error:
        warnings.append('IEEE: '+str(error));sources['IEEE']={'status':'retained_previous','reason':str(error)}
    try:
        release_year=required_year+1
        url=f'https://www.acm.org/media-center/{release_year}/july/impact-factors-{release_year}'
        records=extract_acm(fetch(url).decode('utf-8'),url,required_year);fresh.update(records)
        sources['ACM']={'status':'updated','metric_year':required_year,'count':len(records),'url':url}
        missing=[name for name in ACM_TITLES if name not in records]
        if missing:warnings.append('ACM: no verified new value for '+', '.join(missing))
    except Exception as error:
        warnings.append('ACM: '+str(error));sources['ACM']={'status':'retained_previous','reason':str(error)}
    letpub_updates={}
    for short,identity in LETPUB_JOURNALS.items():
        if short in fresh:continue
        url='https://www.letpub.com.cn/index.php?page=journalapp&view=search&searchissn='+identity['issn']
        try:
            record=extract_letpub(fetch(url).decode('utf-8'),short,url,required_year)
            old=previous.get(short)
            if old and old['metric_year']==required_year and old.get('source_kind')!='secondary':
                if abs(old['jif']-record['jif'])>.0001:
                    raise ValueError('LetPub conflicts with the verified same-year publisher value')
                record=dict(old)
                record['corroborating_source_url']=url
            fresh[short]=record
            letpub_updates[short]='verified'
        except Exception as error:
            warnings.append('LetPub '+short+': '+str(error))
            letpub_updates[short]='retained_previous'
    sources['LetPub']={'journals':letpub_updates}
    if not fresh:raise RuntimeError('No verified publisher data; preserving the previous snapshot. '+'; '.join(warnings))
    merged=merge_metrics(previous,fresh)
    output={'schema_version':1,'updated_at':now.isoformat(timespec='seconds').replace('+00:00','Z'),'requested_metric_year':required_year,'sources':sources,'journals':merged}
    atomic_json(args.output,output)
    for message in warnings:print('::warning::'+message.replace('\n',' '))
    print(f'Saved {len(fresh)} verified journal metrics; {len(merged)} journals retained in total.')

if __name__=='__main__':main()
