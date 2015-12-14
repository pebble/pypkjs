__author__ = 'katharine'

import logging
import requests

from model import TimelineItem, TimelineState, db as database

logger = logging.getLogger('pypkjs.timeline.websync')

class TimelineWebSync(object):
    def __init__(self, urls, oauth):
        self.urls = urls
        self.oauth = oauth

    def _make_request(self, url):
        result = requests.get(url, headers={'Authorization': 'Bearer %s' % self.oauth})
        result.raise_for_status()
        return result.json()

    def _set_url(self, url):
        TimelineState.set("syncURL", url or self.urls.initial_sync)
        return url

    def _get_url(self):
        return TimelineState.get("syncURL", self.urls.initial_sync)

    def update_iter(self):
        url = self._get_url()

        while True:
            logger.debug("requesting %s", url)
            try:
                result = self._make_request(url)
            except requests.RequestException as e:
                logger.error("Request failed: %s", e)
                break
            logger.debug("result: %s", result)

            if result.get('mustResync', False):
                yield 'sync.resync', None
                url = self._set_url(result['syncURL'])
                continue

            for update in result['updates']:
                yield update['type'], update['data']

            if result.get('nextPageURL', None) is not None:
                url = self._set_url(result['nextPageURL'])
            else:
                self._set_url(result.get('syncURL'))
                break
