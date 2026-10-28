#!/usr/bin/env python3
"""Fetch public Scholar summary metrics once; preserve the last good snapshot on failure."""
import argparse
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import urlencode
from urllib.request import Request, urlopen

class ScholarSummaryParser(HTMLParser):
    FIELDS = {'gsc_rsb_std': 'metrics', 'gsc_g_t': 'years', 'gsc_g_al': 'annual'}

    def __init__(self):
        super().__init__()
        self.values = {'metrics': [], 'years': [], 'annual': [], 'name': []}
        self.capture = None
        self.buffer = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        field = next((self.FIELDS[c] for c in attrs.get('class', '').split() if c in self.FIELDS), None)
        if attrs.get('id') == 'gsc_prf_in':
            field = 'name'
        if field and not self.capture:
            self.capture = (tag, field)
            self.buffer = []

    def handle_data(self, data):
        if self.capture:
            self.buffer.append(data)

    def handle_endtag(self, tag):
        if self.capture and tag == self.capture[0]:
            self.values[self.capture[1]].append(''.join(self.buffer).strip())
            self.capture = None
            self.buffer = []


def nonnegative_integer(value):
    value = value.replace(',', '').replace('\u00a0', '').strip()
    if not re.fullmatch(r'\d+', value):
        raise ValueError(f'Invalid Scholar numeric field: {value!r}')
    return int(value)


def parse_profile(document, scholar_id, observed_at=None):
    if not re.fullmatch(r'[A-Za-z0-9_-]{6,32}', scholar_id):
        raise ValueError('Invalid Google Scholar profile ID')
    parser = ScholarSummaryParser()
    parser.feed(document)
    fields = parser.values
    if len(fields['metrics']) != 6 or not fields['name']:
        raise ValueError('Scholar profile metrics were not found; response may be a consent or challenge page')
    if not fields['years'] or len(fields['years']) != len(fields['annual']):
        raise ValueError('Scholar annual citation chart is incomplete')
    totals = [nonnegative_integer(v) for v in fields['metrics']]
    annual = {}
    for year, count in zip(fields['years'], fields['annual']):
        if not re.fullmatch(r'(19|20)\d{2}', year) or year in annual:
            raise ValueError('Invalid or duplicated citation year')
        annual[year] = nonnegative_integer(count)
    if totals[1] > totals[0] or totals[3] > totals[2] or totals[5] > totals[4]:
        raise ValueError('Scholar recent metrics exceed all-time metrics')
    observed_at = observed_at or datetime.now(timezone.utc)
    return {
        'schema_version': 1,
        'scholar_id': scholar_id,
        'name': fields['name'][0],
        'source': 'Google Scholar',
        'profile_url': 'https://scholar.google.com/citations?' + urlencode({'user': scholar_id, 'hl': 'en'}),
        'citedby': totals[0], 'citedby5y': totals[1],
        'hindex': totals[2], 'hindex5y': totals[3],
        'i10index': totals[4], 'i10index5y': totals[5],
        'cites_per_year': dict(sorted(annual.items())),
        'updated_at': observed_at.astimezone(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
    }


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', dir=path.parent, suffix='.tmp', delete=False, encoding='utf-8') as temp:
        json.dump(data, temp, ensure_ascii=False, indent=2)
        temp.write('\n')
        temp_path = Path(temp.name)
    os.replace(temp_path, path)


def save_snapshot(summary, directory):
    directory = Path(directory)
    history_path = directory / 'citation_history.json'
    history = json.loads(history_path.read_text()) if history_path.exists() else []
    if not isinstance(history, list):
        raise ValueError('Existing citation history is malformed; refusing to replace it')
    day = summary['updated_at'][:10]
    history = [row for row in history if row['observed_on'] != day]
    history.append({
        'observed_on': day, 'updated_at': summary['updated_at'],
        'citedby': summary['citedby'], 'hindex': summary['hindex'], 'i10index': summary['i10index'],
    })
    history.sort(key=lambda row: row['observed_on'])
    atomic_json(directory / 'scholar_metrics.json', summary)
    atomic_json(history_path, history)
    # Keep the legacy total-citations badge working. Existing gs_data.json and
    # per-paper citation records are retained, not relabeled as freshly fetched.
    atomic_json(directory / 'gs_data_shieldsio.json', {
        'schemaVersion': 1, 'label': 'citations', 'message': str(summary['citedby']),
    })


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scholar-id', default=os.environ.get('GOOGLE_SCHOLAR_ID', 'mz4NUCAAAAAJ'))
    parser.add_argument('--output-dir', type=Path, default=Path('results'))
    parser.add_argument('--html-file', type=Path, help='Parse a previously fetched profile for offline verification')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]{6,32}', args.scholar_id):
        raise ValueError('Invalid Google Scholar profile ID')
    if args.html_file:
        document = args.html_file.read_text(encoding='utf-8')
    else:
        url = 'https://scholar.google.com/citations?' + urlencode({'user': args.scholar_id, 'hl': 'en'})
        request = Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept-Language': 'en-US,en;q=0.9'})
        # One public profile request. No CAPTCHA solving, proxy rotation or retry loop.
        with urlopen(request, timeout=45) as response:
            document = response.read().decode('utf-8')
    summary = parse_profile(document, args.scholar_id)
    save_snapshot(summary, args.output_dir)
    print(f"Saved Scholar metrics: {summary['citedby']} citations, updated {summary['updated_at']}")

if __name__ == '__main__':
    main()
