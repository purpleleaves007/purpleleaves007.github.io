from pathlib import Path
import re, html, json
OUT=Path(__file__).resolve().parents[1]; SRC=(OUT/'content/profile-source.html').read_text()
def plain(s):return html.unescape(re.sub('<[^>]+>','',s)).strip()
def esc(s):return html.escape(str(s),quote=True)
def icon(name):return f'<svg class="icon" aria-hidden="true"><use href="#i-{name}"></use></svg>'
SPRITE='''<svg class="sprite" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><defs>
<symbol id="i-arrow" viewBox="0 0 24 24"><path d="M6 18 18 6M6 6h12v12"/></symbol>
<symbol id="i-right" viewBox="0 0 24 24"><path d="M4 12h15m-6-6 6 6-6 6"/></symbol>
<symbol id="i-mail" viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="14" rx="1"/><path d="m3 6 9 7 9-7"/></symbol>
<symbol id="i-scholar" viewBox="0 0 24 24"><path d="m2 9 10-5 10 5-10 5L2 9Zm4 3v5c4 3 8 3 12 0v-5m4-3v8"/></symbol>
<symbol id="i-trophy" viewBox="0 0 24 24"><path d="M7 3h10v5c0 4-2 6-5 6s-5-2-5-6V3Zm0 2H3v3c0 3 2 4 5 4m9-7h4v3c0 3-2 4-5 4m-4 2v5m-4 2h8m-7-2h6"/></symbol>
<symbol id="i-medal" viewBox="0 0 24 24"><path d="m8 3 4 7 4-7M4 3h4m8 0h4"/><circle cx="12" cy="16" r="6"/><path d="m12 12 1.2 2.5 2.8.4-2 2 .4 2.7-2.4-1.3-2.4 1.3.4-2.7-2-2 2.8-.4L12 12Z"/></symbol>
<symbol id="i-search" viewBox="0 0 24 24"><circle cx="10" cy="10" r="6"/><path d="m15 15 6 6"/></symbol>
<symbol id="i-menu" viewBox="0 0 24 24"><path d="M4 8h16M4 16h16"/></symbol>
</defs></svg>'''
def header(active='home'):
 links=[('Research','index.html#research','research'),('Impact','index.html#citations','impact'),('Publications','publications.html','publications'),('Awards','awards.html','awards'),('Service','service.html','service'),('About','index.html#about','about')]
 return '<header class="site-header"><div class="container header-inner"><a class="wordmark" href="index.html" aria-label="Xiang Zhang home"><img class="research-logo" src="assets/purpleleaves-maple.png" alt="" aria-hidden="true" width="512" height="512"><span class="wordmark-text">Xiang Zhang <span>章翔</span></span></a><button class="menu-toggle" aria-expanded="false" aria-controls="navigation">Menu '+icon('menu')+'</button><nav class="nav-links" id="navigation" aria-label="Main navigation">'+''.join(f'<a href="{url}"'+(' aria-current="page"' if key==active else '')+f'>{text}</a>' for text,url,key in links)+'<a class="nav-contact" href="mailto:zhangxiang@ieee.org">Get in touch '+icon('arrow')+'</a></nav></div></header>'
def footer(home=False):
 contact='''<section class="contact-section" id="contact"><div><div class="section-kicker">Students & collaborators</div><h2>Good research starts with a conversation.</h2><p>I welcome students and collaborators interested in wireless sensing, IoT security and privacy-preserving ambient intelligence.</p></div><a class="button button-primary" href="mailto:zhangxiang@ieee.org">Let’s talk '''+icon('mail')+'</a></section>' if home else ''
 return '<footer class="container">'+contact+'<div class="footer-bottom"><span>© Xiang Zhang · 章翔 <span aria-hidden="true">/</span> Research & academic profile</span><div><a href="https://scholar.google.com/citations?user=mz4NUCAAAAAJ">Google Scholar '+icon('arrow')+'</a><a href="mailto:zhangxiang@ieee.org">Email '+icon('arrow')+'</a><a class="back-top" href="#top">Back to top ↑</a></div></div></footer>'
def page(title,body,active='home',home=False):return '<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="Xiang Zhang — wireless sensing, IoT security and privacy-preserving ambient intelligence. Research, publications, awards and academic service."><meta name="theme-color" content="#f8f7f3"><title>'+esc(title)+' — Xiang Zhang</title><link rel="icon" href="favicon.ico?v=purpleleaves-v3" sizes="16x16 32x32 48x48"><link rel="icon" type="image/png" sizes="32x32" href="assets/favicon-purpleleaves-32.png"><link rel="apple-touch-icon" sizes="180x180" href="assets/apple-touch-icon-purpleleaves.png"><link rel="stylesheet" href="assets/site.css"><script src="assets/site.js" defer></script></head><body id="top">'+SPRITE+header(active)+body+('<script type="application/json" id="journal-metrics-snapshot">'+json.dumps(json.loads((OUT/'assets/journal-metrics.json').read_text()),ensure_ascii=False).replace('<','\\u003c')+'</script>' if active in ['home','publications'] else '')+footer(home)+'</body></html>'

def extract_list(start):
 frag=SRC[SRC.index(start):];return re.findall(r'<li>(.*?)</li>',frag[frag.index('<ul>'):frag.index('</ul>')],re.S)
confs=extract_list('<h2 id="-conferences"'); journals=extract_list('<h2 id="-journals"')
SHORTS=[('Beyond Physical','ACM IMWUT / UbiComp','Proceedings of the ACM on Interactive, Mobile, Wearable and Ubiquitous Technologies'),('Breaking Coordinate','ACM MobiCom','ACM Annual International Conference on Mobile Computing and Networking'),('AirKey:','ACM MM','ACM International Conference on Multimedia'),('STAR:','NeurIPS','Conference on Neural Information Processing Systems · Datasets and Benchmarks Track'),('Wi-CBR:','AAAI','AAAI Conference on Artificial Intelligence'),('DiffLoc:','USENIX Security','34th USENIX Security Symposium'),('CamLoPa:','IEEE S&P','IEEE Symposium on Security and Privacy'),('A Lightweight','UbiComp Adjunct','Companion of the ACM International Joint Conference on Pervasive and Ubiquitous Computing'),('A Watermark','IEEE ICME','IEEE International Conference on Multimedia & Expo'),('Hidden WiFi','ACM MobiCom','ACM Annual International Conference on Mobile Computing and Networking'),('FacialPulse:','ACM MM','ACM International Conference on Multimedia'),('Mitigating label','IEEE ICME','IEEE International Conference on Multimedia & Expo'),('Real-time vital','IEEE BIBM','IEEE International Conference on Bioinformatics and Biomedicine'),('Wifi-based real','IEEE GLOBECOM','IEEE Global Communications Conference')]
JS=[('Journal on Selected','IEEE JSAC'),('Dependable and Secure','IEEE TDSC'),('Cognitive Communications','IEEE TCCN'),('Sensor Networks','ACM TOSN'),('Affective Computing','IEEE TAFFC'),('Human-Machine','IEEE THMS'),('Internet of Things','IEEE IoT-J'),('Information Forensics','IEEE TIFS'),('Mobile Computing','IEEE TMC'),('Circuits and Systems','IEEE TCSVT'),('Instrumentation','IEEE TIM'),('Computational Social','IEEE TCSS'),('Computational Intelligence Magazine','IEEE CIM')]
records=[]
for index,li in enumerate(confs+journals):
 a=re.search(r'<a href="([^"]+)">(.*?)</a>',li,re.S)
 if a:url,title=a.group(1),plain(a.group(2));tail=li[a.end():]
 else:title=plain(li).split(', Baichuan Wu')[0];url='';tail=li[len(title):]
 venuehtml=list(re.finditer(r'<strong>(.*?)</strong>',li,re.S))[-1]
 venue=plain(venuehtml.group(1));yearmatch=re.search(r'20\d{2}',venue);year=yearmatch.group() if yearmatch else ''
 venue=re.sub(r'\s*20\d{2}\s*','',venue).strip(' ,.');short=venue
 kind='Conference' if index<len(confs) else 'Journal'
 if index<len(confs):
  for prefix,sn,full in SHORTS:
   if title.startswith(prefix):short,venue=sn,full;break
 else:
  for fragment,sn in JS:
   if fragment in venue:short=sn;break
 if title.startswith('Beyond Physical'):kind='Journal'
 code=re.search(r'<code[^>]*>(.*?)</code>',li,re.S);metrics=plain(code.group(1)) if code else ''
 grade=re.search(r'CCF [ABC]',metrics);grade=grade.group() if grade else ''
 quart=re.search(r'JCR Q\d',metrics);quart=quart.group() if quart else ''
 impact=re.search(r'IF\s*=\s*[\d.]+',metrics);impact=impact.group() if impact else ''
 authorhtml=tail[:tail.rfind('<strong>')].strip(' ,.\n\t');authors=re.sub(r'\s+', ' ', plain(authorhtml)).strip(' ,.');authors=re.sub(r',\s*', ', ', authors)
 award='winner' if title.startswith('WiGRUNT:') else 'nominee' if title.startswith('A Watermark') else ''
 notes=[]
 if 'Short Paper' in plain(li):notes.append('Short paper')
 if 'Demo' in plain(li):notes.append('Demo')
 if 'Spotlight' in metrics:notes.append('Spotlight')
 if 'Oral Paper' in metrics:notes.append('Oral paper')
 if title.startswith('A Watermark'):url='https://ieeexplore.ieee.org/document/11209064'
 url=url.replace('http://arxiv.org','https://arxiv.org')
 records.append(dict(title=title,url=url,venue=venue,short=short,year=year,kind=kind,grade=grade,quart=quart,impact=impact,authors=authors,award=award,notes=notes))

JOURNAL_METRICS=json.loads((OUT/'assets/journal-metrics.json').read_text())['journals']
VENUE_CONFIG=json.loads((OUT/'assets/venue-groups.json').read_text())
for record in records:
 record['journal_metrics']=JOURNAL_METRICS.get(record['short']) if record['kind']=='Journal' else None
 record['venue_group']=VENUE_CONFIG['venues'].get(record['short'],'other')
 record['venue_group_label']=VENUE_CONFIG['groups'].get(record['venue_group'],{}).get('label','Unclassified')
 record['contribution_format']='Demo' if 'Demo' in record['notes'] else 'Short Paper' if 'Short paper' in record['notes'] else 'Full Research'

def author_line(r):
 text=esc(r['authors'])
 text=re.sub(r'\bXiang Zhang\b','<strong>Xiang Zhang</strong>',text)
 def marker(m):
  labels=[]
  if '†' in m.group():labels.append('Equal contribution')
  if '*' in m.group():labels.append('Corresponding author')
  return '<sup class="author-mark" title="'+esc('; '.join(labels))+'">'+m.group()+'</sup>'
 text=re.sub(r'[†*]+',marker,text)
 return '<p class="publication-authors">'+text+'</p>'

def venue_badge(r):
 return '<span class="venue-badge venue-group-'+r['venue_group']+'" title="'+esc(r['venue'])+'">'+esc(r['short'])+'</span>'

def rail_award(r):
 if r['award']=='winner':
  return '<span class="rail-award rail-award-winner" title="IEEE SMC Society Andrew P. Sage Best Transactions Paper Award, 2024">'+icon('trophy')+'<span><strong>Best Transactions <br>Paper Award</strong><small>Andrew P. Sage · 2024</small></span></span>'
 if r['award']=='nominee':
  return '<span class="rail-award rail-award-nominee" title="IEEE ICME 2025 Best Paper Award Nomination">'+icon('trophy')+'<span><strong>Best Paper Award <br>Nomination</strong><small>IEEE ICME · 2025</small></span></span>'
 return ''

def tags(r,selected=False):
 t=f'<span class="tag tag-type">{r["kind"]}</span><span class="tag tag-format">{r["contribution_format"]}</span>'
 if r['grade']:t+=f'<span class="tag tag-grade">{r["grade"]}</span>'
 metric=r.get('journal_metrics')
 if metric:
  t+=f'<span class="tag tag-neutral" data-jif-value>IF {metric["jif"]:.1f} · {metric["metric_year"]}</span>'
  t+=f'<span class="tag tag-neutral" data-jif-quartile'+('' if metric.get('quartile') else ' hidden')+'>'+metric.get('quartile','')+'</span>'
 for n in r['notes']:
  if n not in ['Demo','Short paper']:t+=f'<span class="tag tag-neutral">{n}</span>'
 return '<div class="paper-tags"'+(' data-journal-key="'+esc(r['short'])+'"' if r['kind']=='Journal' else '')+'>'+t+'</div>'
selected=[]
for key in ['DiffLoc+:','Breaking Coordinate','DiffLoc:','CamLoPa:','WiGRUNT:','A Watermark']:
 selected.append(next(r for r in records if r['title'].startswith(key)))
HIGHLIGHTS = {
 'DiffLoc+:': 'Extends diffraction-based hidden-camera localization toward more robust operation.',
 'Breaking Coordinate': 'Conditions WiFi pose estimation on device geometry to generalize across transceiver layouts.',
 'DiffLoc:': 'Turns controlled diffraction shadows into camera-bearing estimates without pre-collected training data.',
 'CamLoPa:': 'Uses signal propagation paths to localize hidden wireless cameras.',
 'WiGRUNT:': 'Learns WiFi signal features through dual attention for gesture recognition.',
 'A Watermark': 'Designs watermark updates for image content distributed across multiple stages.',
}
def card(r):
 highlight=next(text for prefix,text in HIGHLIGHTS.items() if r['title'].startswith(prefix))
 anchor=' id="selected-wigrunt"' if r['award']=='winner' else ' id="selected-watermark"' if r['award']=='nominee' else ''
 return f'<a class="paper-card"{anchor} href="{esc(r["url"])}"><div class="selected-rail">'+venue_badge(r)+f'<time class="paper-year">{r["year"]}</time>'+rail_award(r)+'<span class="paper-link">Read paper '+icon('arrow')+f'</span></div><div class="selected-body"><h3 class="paper-title">{esc(r["title"])}</h3><p class="paper-highlight">{esc(highlight)}</p><p class="venue-full">{esc(r["venue"])} · {r["year"]}</p>'+tags(r,True)+'</div></a>'
def heading(kicker,title,link='',url='',description=''):
 return '<div class="section-heading"><div><div class="section-kicker">'+kicker+'</div><h2>'+title+'</h2>'+('<p class="section-description">'+description+'</p>' if description else '')+'</div>'+('<a class="text-link" href="'+url+'">'+link+icon('right')+'</a>' if link else '')+'</div>'
hero='''<main class="container"><section class="hero" aria-label="Introduction"><div class="hero-copy"><div class="eyebrow">Wireless sensing · Security · Ambient intelligence</div><div class="hero-identity"><img class="identity-portrait" src="assets/xiang-zhang.png" alt="Portrait of Xiang Zhang" width="512" height="512"><h1 class="hero-name">Xiang Zhang<span>章翔</span></h1></div><p class="role"><strong>Associate Professor & PhD Supervisor</strong><br>School of Cyber Security · Tianjin University</p><h2 class="research-statement">Wireless sensing.<br><em>Privacy at the core.</em></h2><p class="hero-summary">I explore how wireless signals can understand human behavior and protect privacy — advancing physics-aware sensing and secure ambient intelligence.</p><div class="profile-links"><a href="https://scholar.google.com/citations?user=mz4NUCAAAAAJ">'''+icon('scholar')+'''Google Scholar</a><a href="https://orcid.org/0000-0003-0413-6135">ORCID '''+icon('arrow')+'''</a><a href="mailto:zhangxiang@ieee.org">Email '''+icon('mail')+'''</a></div></div><figure class="research-emblem"><img src="assets/purpleleaves-maple.png" alt="Purple maple leaf with Wi-Fi windows showing a smart city and connected homes" width="512" height="512"><figcaption><span>purpleleaves</span><span>Wireless sensing · Smart environments</span></figcaption></figure></section><div class="venue-strip"><span class="venue-strip-label">RESEARCH<br>APPEARING IN</span><div class="venue-names"><span>IEEE S&P</span><span>USENIX Security</span><span>ACM MobiCom</span><span>IEEE JSAC</span><span>UbiComp</span></div></div>'''
honors='<aside class="honor-band" aria-label="Selected honors"><div class="honor-heading"><span class="section-kicker">Recognition</span><a href="awards.html">All awards '+icon('right')+'</a></div><a class="honor-item" href="awards.html#sage">'+icon('trophy')+'<div><small>IEEE SMC SOCIETY · 2024</small><strong>Andrew P. Sage<br>Best Transactions Paper Award</strong></div></a><a class="honor-item" href="awards.html#hitc">'+icon('medal')+'<div><small>IEEE HITC · 2024</small><strong>Distinguished PhD<br>Dissertation Award</strong></div></a></aside>'
research='<section class="section" id="research">'+heading('01 / Research','Signals. People. Trust.')+'<div class="research-grid">'
for n,title,desc,related,q in [('01','Wireless & human sensing','WiFi-based gesture recognition, 3D pose estimation and physiological sensing — understanding people without cameras or wearables.','MobiCom · IMWUT · THMS','WiFi'),('02','Security in physical spaces','Detecting hidden cameras and studying wireless side channels to protect privacy in everyday environments.','S&P · USENIX Security · JSAC','camera'),('03','Robust ambient intelligence','Physics-aware models and cross-domain learning that help sensing systems adapt beyond a single room or layout.','MobiCom · IMWUT · IoT-J','domain')]:
 research+=f'<article class="research-item"><span class="research-number">{n}</span><h3>{title}</h3><p>{desc}</p><a class="research-related" href="publications.html?q={q}">{related} '+icon('right')+'</a></article>'
research+='</div></section>'
pubs='<section class="section" id="publications">'+heading('03 / Selected publications','Selected work.','All publications','publications.html')+'<div class="paper-grid">'+''.join(card(r) for r in selected)+'</div><div class="publication-footer"><p>Explore the full record across sensing, security and intelligent systems.</p><a class="button" href="publications.html">Browse all publications '+icon('right')+'</a></div></section>'
service='<section class="section service-layout" id="service"><div>'+heading('04 / Academic community','Academic service.',description='Program committees, conference organization, peer review and editorial service.')+'<a class="text-link" href="service.html">View all academic service '+icon('right')+'</a></div><div class="service-list">'
for role,title,detail in [('PC & AREA CHAIR','USENIX Security · IEEE ICME','USENIX Security 2027 · PC Member<br>IEEE ICME 2026 · Area Chair'),('CONFERENCE LEADERSHIP','IEEE ISPA 2025','Publication Chair'),('REVIEWER','MobiCom · ACM MM · AAAI','IMWUT · TMC · TAFFC · TMM · TNNLS …'),('EDITORIAL SERVICE','IoT security & network forensics','Lead Guest Editor · Electronics and AI special issues')]:
 service+=f'<article class="service-row"><span class="service-role">{role}</span><div><h3>{title}</h3><p>{detail}</p></div></article>'
service+='</div></section>'
about='<section class="section about-layout" id="about"><div>'+heading('05 / Background','A research journey.')+'<p class="about-intro">My work connects wireless sensing, security and ambient intelligence, with a long-term interest in privacy-preserving systems for healthcare, smart homes and aging societies.</p><div class="timeline">'
for date,where,what in [('2025.10 — Present','Tianjin University','Associate Professor · School of Cyber Security'),('2023.06 — 2025.09','University of Science and Technology of China','Postdoctoral Fellow'),('2017.06 — 2023.05','Hefei University of Technology','Master’s & doctoral studies'),('During doctoral studies','National Institute of Informatics, Japan','CSC-supported research with Prof. Yusheng Ji'),('2013.09 — 2017.06','Hefei University of Technology','Bachelor of Engineering')]:
 about+=f'<article class="timeline-item"><span class="timeline-date">{date}</span><h3>{where}</h3><p>{what}</p></article>'
about+='</div></div><div>'+heading('06 / Updates','Recently.')
for date,text in [('2026.10','Announced a forthcoming appointment as <strong>Professor (tenure-track) at the Chinese Academy of Sciences</strong>.'),('2026.07','Received the <strong>IEEE ICME Outstanding Area Chair Award</strong>.'),('2026.07','AirKey accepted at <strong>ACM Multimedia 2026</strong>.'),('2026.06','Invited to serve on the <strong>USENIX Security 2027</strong> program committee.')]:
 about+=f'<article class="news-item"><time>{date}</time><p>{text}</p></article>'
about+='<aside class="funding-note"><div class="section-kicker">Research support</div><p>NSFC Young Scientists Fund (Category C)<br>2026–2029 · Grant No. 62502482<br>Anti-WiFi sensing side-channel attacks through cross-technology interference.</p></aside></div></section></main>'
def scholar_panel():
 from datetime import datetime
 from math import ceil
 metrics=json.loads((OUT/'assets/scholar-metrics.json').read_text())
 annual=metrics['cites_per_year']
 max_tick=max(100,ceil(max(annual.values())/100)*100)
 observed_year=int(metrics['updated_at'][:4])
 date_label=datetime.fromisoformat(metrics['updated_at'].replace('Z','+00:00')).strftime('%d %b %Y').lstrip('0')
 bars=''
 for year,count in sorted(annual.items()):
  current=int(year)==observed_year
  bars+=f'<button class="citation-column'+(' is-current' if current else '')+f'" type="button" data-citation-year="{year}" data-citation-count="{count}" style="--value-height:{count/max_tick*100:.3f}%" aria-pressed="'+('true' if current else 'false')+f'" aria-label="{year}: {count} citations'+(' (year to date)' if current else '')+f'"><span class="bar-value">{count}</span><span class="citation-bar" style="height:{count/max_tick*100:.3f}%"></span><span class="bar-year">{year}</span></button>'
 return '<section class="section citation-section" id="citations" data-scholar-url="https://raw.githubusercontent.com/purpleleaves007/purpleleaves007.github.io/google-scholar-stats/scholar_metrics.json" data-scholar-fallback="https://raw.githubusercontent.com/purpleleaves007/purpleleaves007.github.io/google-scholar-stats/gs_data.json">'+heading('02 / Research impact','Citation activity.','Google Scholar',metrics['profile_url'])+f'<div class="citation-layout"><div class="citation-metrics"><span class="metric-label">Total citations</span><strong class="citation-total" id="scholar-total">{metrics["citedby"]:,}</strong><div class="citation-indices"><div><strong id="scholar-hindex">{metrics["hindex"]}</strong><span>h-index</span></div><div><strong id="scholar-i10index">{metrics["i10index"]}</strong><span>i10-index</span></div></div><p class="scholar-sync" id="scholar-sync">Last synced {date_label}</p><span class="tag tag-neutral" id="scholar-status">Google Scholar snapshot</span></div><div class="citation-plot"><div class="chart-heading"><h3>Citations per year</h3><span id="scholar-ytd">{observed_year} · year to date</span></div><div class="chart-area"><div class="chart-axis" aria-hidden="true"><span>{max_tick}</span><span>{max_tick//2}</span><span>0</span></div><div class="citation-bars" id="citation-bars">{bars}</div></div><p class="citation-detail" id="citation-detail" aria-live="polite">'+str(observed_year)+' · '+str(annual.get(str(observed_year),0))+' citations · year to date</p></div></div><script type="application/json" id="scholar-snapshot">'+json.dumps(metrics,ensure_ascii=False).replace('<','\\u003c')+'</script></section>'
impact=scholar_panel()
(OUT/'index.html').write_text(page('Research & academic profile',hero+honors+research+impact+pubs+service+about,home=True))

def archive_head(title,kicker,description,count,label):
 return '<main class="container archive"><div class="breadcrumbs"><a href="index.html">Home</a><span>/</span><span>'+title+'</span></div><section class="archive-hero"><div><div class="eyebrow">'+kicker+'</div><h1>'+title+'</h1><p>'+description+'</p></div><div class="archive-count">'+str(count)+'<span>'+label+'</span></div></section>'
def filterbar(types,search,extra=''):
 return '<div class="filter-bar"><div class="segmented" role="group" aria-label="Filter by type">'+''.join('<button type="button" data-filter="'+value+'" aria-pressed="'+('true' if i==0 else 'false')+'">'+text+'</button>' for i,(text,value) in enumerate(types))+'</div><label class="search-wrap">'+icon('search')+'<input id="record-search" type="search" aria-label="Search directory" placeholder="'+search+'"></label>'+extra+'</div><div class="result-line"><span id="result-count" role="status" aria-live="polite"></span><button type="button" class="reset-button" id="reset-filters">Reset filters</button></div>'
def empty():return '<div class="empty-state" id="empty-state" hidden><h2>No matching entries.</h2><p>Try another keyword or clear the filters.</p><button type="button" class="button" data-reset>Clear all filters '+icon('right')+'</button></div>'
def record_attrs(r):return 'data-record data-kind="'+r['kind']+'" data-year="'+r.get('year','')+'" data-grade="'+r.get('grade','')+'" data-venue-group="'+r.get('venue_group','')+'" data-paper-type="'+r.get('contribution_format','')+'"'
body=archive_head('Publications.','Research / Complete record','Wireless sensing, security and ambient intelligence. Browse by type, year or venue; every entry includes its full title and publication venue.',len(records),'publications')+'<section class="archive-content" aria-label="Publication directory">'
years=sorted({r['year'] for r in records if r['year']},reverse=True)
extra='<select id="year-filter" aria-label="Filter by year"><option value="all">All years</option>'+''.join(f'<option>{y}</option>' for y in years)+'<option value="unspecified">Year unspecified</option></select><select id="grade-filter" aria-label="Filter by CCF rank"><option value="all">All CCF ranks</option><option>CCF A</option><option>CCF B</option><option>CCF C</option></select>'
extra+='<select id="format-filter" aria-label="Filter by paper type"><option value="all">All paper types</option><option value="Full Research">Full Research</option><option value="Demo">Demo</option><option value="Short Paper">Short Paper</option></select>'
body+=filterbar([('All publications','all'),('Conferences','Conference'),('Journals','Journal')],'Search titles, venues, authors…',extra)
body+='<p class="authors-legend"><span><sup>*</sup> Corresponding author</span><span><sup>†</sup> Equal contribution</span></p>'
for r in sorted(records,key=lambda r:(-int(r['year'] or '0'),VENUE_CONFIG['groups'].get(r['venue_group'],{}).get('priority',99))):
 title='<a href="'+esc(r['url'])+'">'+esc(r['title'])+'</a>' if r['url'] else esc(r['title'])
 body+='<article class="publication-entry" '+record_attrs(r)+'><div class="entry-rail">'+venue_badge(r)+'<span class="paper-year">'+(r['year'] or 'Year unspecified')+'</span>'+rail_award(r)+'</div><div class="entry-body"><h2 class="paper-title">'+title+'</h2>'+author_line(r)+'<p class="venue-full">'+esc(r['venue'])+(' · '+r['year'] if r['year'] else '')+'</p>'+tags(r)
 body+='<div class="entry-tools">'+('<a class="paper-link" href="'+esc(r['url'])+'">Read paper '+icon('arrow')+'</a>' if r['url'] else '<span class="paper-year">Paper link not listed</span>')+'</div>'
 body+='</div></article>'
body+=empty()+'</section></main>'
(OUT/'publications.html').write_text(page('Publications',body,'publications'))

award_rows=[('2026.07','IEEE ICME Outstanding Area Chair Award','IEEE International Conference on Multimedia & Expo · 2026','winner','Service award','https://2026.ieeeicme.org/awards/','icme-ac'),('2025.07','IEEE ICME Best Paper Award Nomination','A Watermark Updating Framework for Multi-stage Image Content Distribution','nominee','Best Paper Award Nomination','https://2025.ieeeicme.org/awards/','icme-nomination'),('2024.11','IEEE HITC Distinguished PhD Dissertation Award','IEEE Technical Committee on Hyper-Intelligence','winner','Dissertation award','https://ieee-hyperintelligence.org/award','hitc'),('2024.10','Andrew P. Sage Best Transactions Paper Award','IEEE Systems, Man, and Cybernetics Society · WiGRUNT','winner','Best Transactions Paper Award','https://www.ieeesmc.org/about-smcs/awards/andrew-p-sage-best-transactions-paper/','sage'),('2020.09','China Scholarship Council — Joint Doctoral Program','China Scholarship Council','scholarship','Scholarship','','csc'),('2019.10','National Scholarship — Doctoral Studies','Ministry of Education of P. R. China','scholarship','Scholarship','','national')]
body=archive_head('Honors & awards.','Recognition / Complete record','Paper awards, doctoral recognition, academic service awards and scholarships.',6,'honors & awards')+'<section class="archive-content" aria-label="Awards directory">'+filterbar([('All honors','all'),('Awards','winner'),('Nominations','nominee'),('Scholarships','scholarship')],'Search awards, organizations, years…')
for date,title,desc,kind,label,url,aid in award_rows:
 symbol='scholar' if kind=='scholarship' else 'medal' if aid=='hitc' else 'trophy'
 body+='<article class="award-entry" id="'+aid+'" data-record data-kind="'+kind+'"><time class="award-date">'+date+'</time><div class="award-icon '+kind+'">'+icon(symbol)+'</div><div><h2>'+title+'</h2><p>'+desc+'</p><span class="tag tag-'+('nominee' if kind=='nominee' else 'winner' if kind=='winner' else 'grade')+'">'+(icon('trophy') if kind in ['nominee','winner'] else '')+label+'</span></div>'+('<a href="'+url+'">Award details '+icon('arrow')+'</a>' if url else '')+'</article>'
body+=empty()+'</section></main>'
(OUT/'awards.html').write_text(page('Honors & awards',body,'awards'))

rawservice=extract_list('<h1 id="-tpc-member-editor-and-reviewers"')
# Keep every source entry, grouped by its explicitly stated type. No unspecified role is inferred.
groups=[('Conference leadership','Publication and conference organization.','Leadership',[(0,'Publication Chair · ISPA 2025')]),('PC, area chairs & committees','Program committees, area chairs and conference service.','Committee',[(i,'Area Chair · ICME 2026' if i==4 else '') for i in [1,2,3,4,5,6,7,8,9,10]]),('Reviewing','Journal peer review. Conference reviewing is also listed with conference service.','Reviewer',[(i,'') for i in range(11,21)]),('Editorial service','Special issues and guest editing.','Editorial',[(21,'Lead Guest Editor'),(22,'Lead Guest Editor')])]
body=archive_head('Academic service.','Community / Complete record','Program committees and area chairs, conference organization, editorial work and peer review.',23,'service records')+'<section class="archive-content" aria-label="Academic service directory">'+filterbar([('All service','all'),('Leadership','Leadership'),('PC & committees','Committee'),('Reviewing','Reviewer'),('Editorial','Editorial')],'Search conferences, journals, roles…')
for title,desc,kind,entries in groups:
 body+='<section class="service-group" data-record-group><div class="service-group-heading"><h2>'+title+'</h2><p>'+desc+'</p></div><div>'
 for i,role in entries:
  text=plain(rawservice[i]).replace('Usenix','USENIX').replace('Mobicom','MobiCom')
  # Only remove a repeated role when shown as an explicit separate label.
  if role:text=text.replace(', Publication Chair','').replace(', Area Chair','').replace(' (Lead Guest Editor)','')
  body+='<article class="service-record" data-record data-kind="'+kind+'"><h3>'+esc(text)+'</h3>'+('<span class="tag tag-grade">'+esc(role)+'</span>' if role else '')+'</article>'
 body+='</div></section>'
body+=empty()+'</section></main>'
(OUT/'service.html').write_text(page('Academic service',body,'service'))
(OUT/'assets/publications.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))
print('Built four pages with',len(records),'publication records,',len(award_rows),'awards and',len(rawservice),'service records.')
