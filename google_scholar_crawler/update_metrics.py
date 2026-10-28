#!/usr/bin/env python3
"""Fetch public Scholar summary metrics once; preserve the last good snapshot on failure."""
import argparse
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlsplit
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
        raise ValueError('Invalid Scholar numeric field')
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


class ProviderError(RuntimeError):
    """A request failure whose message never contains a credential-bearing URL."""


def parse_serpapi(payload, scholar_id, observed_at=None):
    """Read Google Scholar metrics via SerpApi without changing citation source."""
    if not re.fullmatch(r'[A-Za-z0-9_-]{6,32}', scholar_id):
        raise ValueError('Invalid Google Scholar profile ID')
    observed_at = observed_at or datetime.now(timezone.utc)
    if not isinstance(payload, dict) or payload.get('error'):
        raise ValueError('SerpApi did not return a successful author result')
    parameters = payload.get('search_parameters', {})
    metadata = payload.get('search_metadata', {})
    if parameters.get('engine') != 'google_scholar_author' or parameters.get('author_id') != scholar_id:
        raise ValueError('SerpApi returned an unexpected author identity')
    profile = urlsplit(metadata.get('google_scholar_author_url', ''))
    if profile.scheme != 'https' or profile.hostname != 'scholar.google.com' or parse_qs(profile.query).get('user') != [scholar_id]:
        raise ValueError('SerpApi Scholar profile URL does not match the requested author')
    if metadata.get('status') != 'Success':
        raise ValueError('SerpApi search is incomplete')
    timestamp = metadata.get('processed_at') or metadata.get('created_at')
    if not isinstance(timestamp, str):
        raise ValueError('SerpApi result has no observation timestamp')
    try:
        updated = datetime.fromisoformat(timestamp.replace(' UTC', '+00:00').replace('Z', '+00:00'))
    except ValueError:
        raise ValueError('SerpApi observation timestamp is invalid') from None
    if updated.tzinfo is None or updated.timestamp() > observed_at.timestamp() + 300:
        raise ValueError('SerpApi observation timestamp is invalid')
    name = payload.get('author', {}).get('name')
    if not isinstance(name, str) or not name.strip():
        raise ValueError('SerpApi author name is missing')
    cited_by = payload.get('cited_by', {})
    table = {}
    for row in cited_by.get('table', []):
        if not isinstance(row, dict):
            raise ValueError('SerpApi metrics table is malformed')
        for key, value in row.items():
            if key in table:
                raise ValueError('SerpApi contains duplicated citation metrics')
            table[key] = value
    totals = []
    recent_periods = set()
    for key in ['citations', 'h_index', 'i10_index']:
        values = table.get(key)
        if not isinstance(values, dict) or 'all' not in values:
            raise ValueError('SerpApi citation metrics are incomplete')
        recent = [k for k in values if re.fullmatch(r'since_20\d{2}', k)]
        if len(recent) != 1:
            raise ValueError('SerpApi recent citation metrics are incomplete')
        recent_periods.add(recent[0])
        totals.extend(nonnegative_integer(str(values[k])) for k in ['all', recent[0]])
    if len(recent_periods) != 1:
        raise ValueError('SerpApi citation metrics use inconsistent recent periods')
    if any(totals[i + 1] > totals[i] for i in [0, 2, 4]):
        raise ValueError('Scholar recent metrics exceed all-time metrics')
    annual = {}
    for row in cited_by.get('graph', []):
        if not isinstance(row, dict):
            raise ValueError('SerpApi annual citation chart is malformed')
        year = str(row.get('year', ''))
        if not re.fullmatch(r'(19|20)\d{2}', year) or year in annual or int(year) > observed_at.year:
            raise ValueError('SerpApi citation year is invalid or duplicated')
        annual[year] = nonnegative_integer(str(row.get('citations', '')))
    if not annual:
        raise ValueError('SerpApi annual citation chart is missing')
    return {
        'schema_version': 1, 'scholar_id': scholar_id, 'name': name.strip(),
        'source': 'Google Scholar', 'retrieved_via': 'SerpApi',
        'profile_url': 'https://scholar.google.com/citations?' + urlencode({'user': scholar_id, 'hl': 'en'}),
        'citedby': totals[0], 'citedby5y': totals[1],
        'hindex': totals[2], 'hindex5y': totals[3],
        'i10index': totals[4], 'i10index5y': totals[5],
        'cites_per_year': dict(sorted(annual.items())),
        'updated_at': updated.astimezone(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
    }


def fetch_summary(scholar_id, provider='auto', api_key=None):
    if provider not in {'auto', 'direct', 'serpapi'}:
        raise ValueError('Unsupported Scholar transport')
    provider = ('serpapi' if api_key else 'direct') if provider == 'auto' else provider
    if provider == 'serpapi':
        if not api_key:
            raise ProviderError('Set the SERPAPI_API_KEY repository secret to enable Google Scholar API updates')
        url = 'https://serpapi.com/search.json?' + urlencode({
            'engine': 'google_scholar_author', 'author_id': scholar_id,
            'hl': 'en', 'api_key': api_key,
        })
    else:
        url = 'https://scholar.google.com/citations?' + urlencode({'user': scholar_id, 'hl': 'en'})
    request = Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept-Language': 'en-US,en;q=0.9'})
    try:
        with urlopen(request, timeout=45) as response:
            document = response.read().decode('utf-8')
    except HTTPError as error:
        if provider == 'direct' and error.code in {403, 429}:
            raise ProviderError(f'Google Scholar refused the runner request (HTTP {error.code}). Set SERPAPI_API_KEY to use the Google Scholar Author API. Existing metrics were retained.') from None
        raise ProviderError(f'{provider} request failed (HTTP {error.code}); existing metrics were retained') from None
    except (URLError, TimeoutError, OSError):
        raise ProviderError(f'{provider} could not be reached; existing metrics were retained') from None
    if provider == 'serpapi':
        try:
            payload = json.loads(document)
        except json.JSONDecodeError:
            raise ValueError('SerpApi returned invalid JSON') from None
        return parse_serpapi(payload, scholar_id)
    return parse_profile(document, scholar_id)


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', dir=path.parent, suffix='.tmp', delete=False, encoding='utf-8') as temp:
        json.dump(data, temp, ensure_ascii=False, indent=2)
        temp.write('\n')
        temp_path = Path(temp.name)
    os.replace(temp_path, path)


def save_snapshot(summary, directory):
    directory = Path(directory)
    current_path = directory / 'scholar_metrics.json'
    if current_path.exists():
        current = json.loads(current_path.read_text())
        if current.get('scholar_id') != summary['scholar_id']:
            raise ValueError('Existing citation data belongs to a different Scholar author')
        if current.get('updated_at', '') > summary['updated_at']:
            return False
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
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scholar-id', default=os.environ.get('GOOGLE_SCHOLAR_ID', 'mz4NUCAAAAAJ'))
    parser.add_argument('--output-dir', type=Path, default=Path('results'))
    parser.add_argument('--provider', choices=['auto', 'direct', 'serpapi'], default=os.environ.get('GOOGLE_SCHOLAR_PROVIDER', 'auto'))
    offline = parser.add_mutually_exclusive_group()
    offline.add_argument('--html-file', type=Path, help='Parse a previously fetched profile for offline verification')
    offline.add_argument('--json-file', type=Path, help='Parse a previously fetched SerpApi result for offline verification')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]{6,32}', args.scholar_id):
        raise ValueError('Invalid Google Scholar profile ID')
    try:
        if args.html_file:
            summary = parse_profile(args.html_file.read_text(encoding='utf-8'), args.scholar_id)
        elif args.json_file:
            summary = parse_serpapi(json.loads(args.json_file.read_text(encoding='utf-8')), args.scholar_id)
        else:
            summary = fetch_summary(args.scholar_id, args.provider, os.environ.get('SERPAPI_API_KEY'))
        saved = save_snapshot(summary, args.output_dir)
    except ProviderError as error:
        print(str(error), file=sys.stderr)
        return 1
    except (ValueError, OSError):
        # Do not print raw request exceptions or provider bodies: their URLs may
        # contain an API key. The workflow displays only a fixed diagnostic.
        print('Google Scholar update failed. Check the transport / SERPAPI_API_KEY configuration. The last verified snapshot was retained.', file=sys.stderr)
        return 1
    if saved:
        print(f"Saved Scholar metrics: {summary['citedby']} citations, observed {summary['updated_at']}")
    else:
        print(f"Kept the newer existing snapshot; provider result was observed {summary['updated_at']}")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
