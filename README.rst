Requests-NSURLSession
=====================

Integration for the Darwin `NSURLSession`_ API for Requests.

This module provides a Requests `Transport Adapter`_ that changes the HTTP
backend of Requests from `urllib3`_ to `NSURLSession`_. This API, available
on modern Darwin platforms like macOS, iOS, watchOS, and tvOS, provides a rich
set of functionality to applications that wish to use HTTP. In particular, it
provides extremely featureful ties into the operating system itself, allowing
the use of caching, TLS, and other features that are not normally available to
Python applications.

Using Requests-NSURLSession is extremely simple:

.. code-block:: python

    import requests
    from requests_nsurlsession.adapter import NSURLSessionAdapter

    session = requests.Session()
    adapter = NSURLSessionAdapter()
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    response = session.get('http://http2bin.org/get')

Work In Progress
----------------

Warning! This is very much a work in progress, and a substantial quantity of
functionality is currently missing. Only the most basic HTTP requests can be
served at this time, and many Requests features do not function as you'd
expect them to.

Please feel free to try this out or to help develop features, but be aware that
this is not even close to feature complete at this time.

License
-------

This code is available under the MIT license. See LICENSE for more details.
