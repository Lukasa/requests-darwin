# -*- coding: utf-8 -*-
"""
Defines the Requests Transport Adapter that uses NSURLSession.
"""
from requests.adapters import BaseAdapter

import Foundation


class NSURLSessionAdapter(BaseAdapter):
    """
    A Requests Transport Adapter that uses NSURLSession to dispatch requests,
    rather than using urllib3.

    This adapter takes advantage of the native networking support in
    Darwin-based operating systems (such as macOS, iOS, watchOS, and tvOS),
    while maintaining the APIs of the extremely popular Python Requests
    library.
    """
    def __init__(self, *args, **kwargs):
        super(NSURLSessionAdapter, self).__init__(*args, **kwargs)

    def close(self):
        # TODO
        pass

    def send(self, request, stream=False, timeout=None, verify=True, cert=None,
             proxies=None):
        """
        Send a given request.
        """
        # TODO
        pass
