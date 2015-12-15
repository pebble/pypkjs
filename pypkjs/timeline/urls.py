from __future__ import absolute_import
__author__ = 'katharine'

import os


class URLManager(object):
    def __init__(self):
        self.internal_api_root = os.environ.get("PEBBLE_TIMELINE_INTERNAL_API", "https://timeline-sync.getpebble.com")
        self.public_api_root = os.environ.get("PEBBLE_TIMELINE_PUBLIC_API", "https://timeline-api.getpebble.com")

    @property
    def fw_resource_map(self):
        return "http://pebblefw.s3.amazonaws.com/pebble/snowy_dvt/release_v3/layouts/v3.0-dp4_layouts.json"

    @property
    def sandbox_token(self):
        return self.internal_api_root + "/v1/tokens/sandbox/%s"

    @property
    def manage_subscription(self):
        return self.public_api_root + "/v1/user/subscriptions/%s"

    @property
    def app_subscription_list(self):
        return self.public_api_root + "/v1/user/subscriptions"

    @property
    def initial_sync(self):
        return self.internal_api_root + "/v1/sync"
