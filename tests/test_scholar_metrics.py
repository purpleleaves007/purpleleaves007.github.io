"""Protect metric provenance, cache freshness and API-key confidentiality."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

from google_scholar_crawler import update_metrics as metrics

ID = 'mz4NUCAAAAAJ'
OBSERVED = datetime(2026, 10, 28, 10, 0, tzinfo=timezone.utc)


def result():
    # Synthetic transport fixture, based on the published SerpApi response schema.
    # It is not presented as a successful live SerpApi request.
    return {
        'search_parameters': {'engine': 'google_scholar_author', 'author_id': ID},
        'search_metadata': {
            'status': 'Success', 'processed_at': '2026-10-28 09:00:00 UTC',
            'google_scholar_author_url': 'https://scholar.google.com/citations?user=' + ID,
        },
        'author': {'name': 'Xiang Zhang'},
        'cited_by': {
            'table': [
                {'citations': {'all': 1285, 'since_2021': 1265}},
                {'h_index': {'all': 20, 'since_2021': 20}},
                {'i10_index': {'all': 25, 'since_2021': 25}},
            ],
            'graph': [{'year': 2025, 'citations': '538'}, {'year': 2026, 'citations': 345}],
        },
    }


class ScholarTransportTests(unittest.TestCase):
    def test_api_preserves_google_scholar_provenance_and_original_observation_time(self):
        snapshot = metrics.parse_serpapi(result(), ID, OBSERVED)
        self.assertEqual(snapshot['source'], 'Google Scholar')
        self.assertEqual(snapshot['retrieved_via'], 'SerpApi')
        self.assertEqual(snapshot['updated_at'], '2026-10-28T09:00:00Z')
        self.assertEqual((snapshot['citedby'], snapshot['hindex'], snapshot['i10index']), (1285, 20, 25))
        self.assertEqual(snapshot['cites_per_year'], {'2025': 538, '2026': 345})

    def test_rejects_wrong_author_id_even_if_name_matches(self):
        raw = result(); raw['search_parameters']['author_id'] = 'SomeoneElse'
        with self.assertRaises(ValueError): metrics.parse_serpapi(raw, ID, OBSERVED)

    def test_rejects_mismatched_profile_url(self):
        raw = result(); raw['search_metadata']['google_scholar_author_url'] += 'WRONG'
        with self.assertRaises(ValueError): metrics.parse_serpapi(raw, ID, OBSERVED)

    def test_incomplete_and_failed_results_are_rejected(self):
        for status in ['Processing', 'Error', None]:
            raw = result(); raw['search_metadata']['status'] = status
            with self.assertRaises(ValueError): metrics.parse_serpapi(raw, ID, OBSERVED)

    def test_missing_metrics_do_not_silently_become_zero(self):
        raw = result(); raw['cited_by']['table'].pop()
        with self.assertRaises(ValueError): metrics.parse_serpapi(raw, ID, OBSERVED)

    def test_recent_metrics_cannot_exceed_lifetime_metrics(self):
        raw = result(); raw['cited_by']['table'][0]['citations']['since_2021'] = 9999
        with self.assertRaises(ValueError): metrics.parse_serpapi(raw, ID, OBSERVED)

    def test_all_recent_metrics_must_cover_the_same_period(self):
        raw = result(); raw['cited_by']['table'][1]['h_index'] = {'all': 20, 'since_2016': 20}
        with self.assertRaises(ValueError): metrics.parse_serpapi(raw, ID, OBSERVED)

    def test_missing_duplicate_and_future_chart_years_are_rejected(self):
        for graph in [[], [{'year': 2026, 'citations': 1}] * 2, [{'year': 2099, 'citations': 1}]]:
            raw = result(); raw['cited_by']['graph'] = graph
            with self.assertRaises(ValueError): metrics.parse_serpapi(raw, ID, OBSERVED)

    def test_cached_api_result_does_not_get_a_new_fake_timestamp(self):
        raw = result(); raw['search_metadata']['processed_at'] = '2026-10-20T09:00:00Z'
        self.assertEqual(metrics.parse_serpapi(raw, ID, OBSERVED)['updated_at'], '2026-10-20T09:00:00Z')

    def test_future_and_timezone_free_observation_times_are_rejected(self):
        for timestamp in ['2026-10-29T09:00:00Z', '2026-10-28T09:00:00', 'invalid']:
            raw = result(); raw['search_metadata']['processed_at'] = timestamp
            with self.assertRaises(ValueError): metrics.parse_serpapi(raw, ID, OBSERVED)

    def test_network_exception_does_not_disclose_api_key(self):
        secret = 'private-key-never-print-this'
        url = 'https://serpapi.com/search.json?api_key=' + secret
        with patch.object(metrics, 'urlopen', side_effect=HTTPError(url, 401, secret, {}, None)):
            with self.assertRaises(metrics.ProviderError) as caught:
                metrics.fetch_summary(ID, 'serpapi', secret)
        self.assertNotIn(secret, str(caught.exception))
        self.assertIn('401', str(caught.exception))

    def test_missing_api_key_is_rejected_before_request(self):
        with patch.object(metrics, 'urlopen') as request:
            with self.assertRaises(metrics.ProviderError): metrics.fetch_summary(ID, 'serpapi')
            request.assert_not_called()

    def test_auto_selects_api_when_key_is_present(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(result()).encode()
        with patch.object(metrics, 'urlopen', return_value=response) as request:
            snapshot = metrics.fetch_summary(ID, 'auto', 'test-only-key')
        self.assertEqual(snapshot['retrieved_via'], 'SerpApi')
        self.assertTrue(request.call_args.args[0].full_url.startswith('https://serpapi.com/search.json?'))

    def test_older_provider_cache_cannot_replace_newer_snapshot_or_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            current = metrics.parse_serpapi(result(), ID, OBSERVED)
            metrics.save_snapshot(current, Path(tmp))
            before = {p.name: p.read_bytes() for p in Path(tmp).iterdir()}
            old = deepcopy(current); old['updated_at'] = '2026-10-20T09:00:00Z'
            self.assertFalse(metrics.save_snapshot(old, Path(tmp)))
            self.assertEqual(before, {p.name: p.read_bytes() for p in Path(tmp).iterdir()})

    def test_same_day_success_updates_history_without_duplicating_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            snapshot = metrics.parse_serpapi(result(), ID, OBSERVED)
            metrics.save_snapshot(snapshot, Path(tmp)); metrics.save_snapshot(snapshot, Path(tmp))
            history = json.loads((Path(tmp) / 'citation_history.json').read_text())
            self.assertEqual(len(history), 1)


if __name__ == '__main__':
    unittest.main()
