# -*- coding: utf-8 -*-
"""
Defines the Requests Transport Adapter that uses NSURLSession.
"""
import objc

from requests.adapters import BaseAdapter
from requests.models import Response
from requests.structures import CaseInsensitiveDict
from requests.utils import get_encoding_from_headers

from Foundation import (
    NSURLSessionConfiguration, NSURLSession, NSObject, NSMutableURLRequest,
    NSURL, NSURLSessionResponseAllow,
    NSURLSessionAuthChallengePerformDefaultHandling
)
from PyObjCTools.KeyValueCoding import getKey


try:
    from Queue import Queue
except ImportError:
    from queue import Queue


# These headers are reserved to the NSURLSession and should not be set by
# Requests, though we may use them.
_RESERVED_HEADERS = set([
    'authorization', 'connection', 'host', 'proxy-authenticate',
    'proxy-authorization', 'www-authenticate',
])


class _RequestsDelegate(NSObject):
    """
    This delegate implements certain callbacks that NSURLSession will make to
    determine bits of information in the middle of requests. This allows
    NSURLSession to return control immediately, while still asking the
    application for more details.
    """
    def initWithAdapter_(self, adapter):
        self = objc.super(_RequestsDelegate, self).init()
        if self is None:
            return None

        # Save a reference to the adapter. This will let us call back into it
        # to handle things.
        self._adapter = adapter
        return self

    def URLSession_task_didCompleteWithError_(self, session, task, error):
        """
        Tells the delegate that the task finished transferring data.

        Server errors are not reported through the error parameter. The only
        errors this delegate receives through the error parameter are
        client-side errors, such as being unable to resolve the hostname or
        connect to the host.

        :param session: The session containing the task whose request finished
            transferring data.
        :type session: NSURLSession

        :param task: The task whose request finished transferring data.
        :type task: NSURLSessionTask

        :param error: If an error occurred, an error object indicating how the
            transfer failed, otherwise None.
        :type error: NSError or None

        :returns: Nothing
        """
        if error is not None:
            self._adapter._receive_error(task, error)

    def URLSession_task_didReceiveChallenge_completionHandler_(self, session,
                                                               task, challenge,
                                                               handler):
        """
        Requests credentials from the delegate in response to an authentication
        request from the remote server.

        :param session: The session containing the task whose request requires
            authentication.
        :type session: NSURLSession

        :param task: The task whose request requires authentication.
        :type task: NSURLSessionTask

        :param challenge: An object that contains the request for
            authentication.
        :type challenge: NSURLAuthenticationChallenge

        :param handler: A handler that this method calls. Its parameters are:

            - ``disposition``: One of several constants that describes how the
              challenge should be handled.
            - ``credential``: The credential that should be used for
              authentication if disposition is
              ``NSURLSessionAuthChallengeUseCredential``; otherwise, None.

        :type handler: Function taking two arguments. First is of type
            NSURLSessionAuthChallengeDisposition, second is of NSURLCredential.

        :returns: Nothing
        """
        # TODO: Here we'll handle all of auth, verify, and cert. For now, just
        # do the default.
        handler(NSURLSessionAuthChallengePerformDefaultHandling, None)

    def URLSession_task_didSendBodyData_totalBytesSent_totalBytesExpectedToSend_(self,
                                                                                 session,
                                                                                 task,
                                                                                 bytesSent,
                                                                                 totalBytesSent,
                                                                                 totalBytesExpectedToSend):
        """
        Periodically informs the delegate of the progress of sending body
        content to the server.

        Requests doesn't care about this method, so it's a no-op.
        """
        pass

    def URLSession_task_needNewBodyStream_(self, session, task, handler):
        """
        Tells the delegate when a task requires a new request body stream to
        send to the remote server.

        This delegate method is called under two circumstances:

        1. To provide the initial request body stream if the task was created
           with uploadTaskWithStreamedRequest:
        2. To provide a replacement request body stream if the task needs to
           resend a request that has a body stream because of an authentication
           challenge or other recoverable server error.

        :param session: The session containing the task that needs a new body
            stream.
        :type session: NSURLSession

        :param task: The task that needs a new body stream.
        :type task: NSURLSessionTask

        :param handler: A completion handler that your delegate method should
            call with the new body stream.
        :type handler: Function taking one argument, a NSInputStream.

        :returns: Nothing.
        """
        pass


    def URLSession_task_willPerformHTTPRedirection_newRequest_completionHandler_(self,
                                                                                 session,
                                                                                 task,
                                                                                 response,
                                                                                 request,
                                                                                 handler):
        """
        Tells the delegate that the remote server requested an HTTP redirect.

        Requests handles its own redirects, so we always refuse. We do this by
        calling the completion handler with ``None``.
        """
        handler(None)

    def URLSession_dataTask_didReceiveResponse_completionHandler_(self,
                                                                  session,
                                                                  dataTask,
                                                                  response,
                                                                  handler):
        """
        Tells the delegate that the data task received the initial reply
        (headers) from the server.

        :param session: The session containing the data task that received an
            initial reply.
        :type session: NSURLSession

        :param task: The data task that received an initial reply.
        :type task: NSURLSessionDataTask

        :param response: A URL response object populated with headers.
        :type response: NSURLResponse

        :param handler: A completion handler that our code calls to continue
            the transfer, passing a constant to indicate whether the transfer
            should continue as a data task or should become a download task.

            - If we pass NSURLSessionResponseAllow, the task continues
              normally.
            - If we pass NSURLSessionResponseCancel, the task is canceled.
            - If we pass NSURLSessionResponseBecomeDownload as the disposition,
              our delegate’s ``URLSession:dataTask:didBecomeDownloadTask:``
              method is called to provide you with the new download task that
              supersedes the current task.

        :type handler: Function that takes one argument, a
            ``NSURLSessionResponseDisposition``.

        :returns: Nothing.
        """
        self._adapter._receive_response(dataTask, response)
        handler(NSURLSessionResponseAllow)

    def URLSession_dataTask_didBecomeDownloadTask_(self, session, dataTask,
                                                   downloadTask):
        """
        Requests does not use download tasks, so this method is never called.
        """
        pass

    def URLSession_dataTask_didBecomeStreamTask(self, session, dataTask,
                                                streamTask):
        """
        Requests never converts into stream tasks.
        """
        pass

    def URLSession_dataTask_didReceiveData_(self, session, dataTask, data):
        """
        Tells the delegate that the data task has received some of the expected
        data.

        Because the NSData object is often pieced together from a number of
        different data objects, whenever possible, use NSData’s
        ``enumerateByteRangesUsingBlock:`` method to iterate through the data
        rather than using the bytes method (which flattens the NSData object
        into a single memory block).

        This delegate method may be called more than once, and each call
        provides only data received since the previous call. The app is
        responsible for accumulating this data if needed.

        :param session: The session containing the data task that provided
            data.
        :type session: NSURLSession

        :param task: The data task that provided data.
        :type task: NSURLSessionDataTask

        :param data: A data object containing the transferred data.
        :type data: NSData

        :returns: Nothing
        """
        pass


def _build_NSRequest(request, timeout):
    """
    Converts a Requests request into an NSRequest. Does not touch the
    request body: that's handled elsewhere.
    """
    nsrequest = NSMutableURLRequest.requestWithURL_(
        NSURL.URLWithString_(request.url)
    )
    nsrequest.setHTTPMethod_(request.method)
    if timeout is not None:
        nsrequest.timeoutInterval = float(timeout)

    for k, v in request.headers.items():
        k, v = k.lower(), v.lower()

        if k in _RESERVED_HEADERS:
            continue

        # Yes, this is backwards on purpose, Foundation has a weird API.
        nsrequest.setValue_forHTTPHeaderField_(v, k)

    return nsrequest


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

        self._delegate = None
        self._session = None
        self._tasks = {}

        self._initialize_session()

    def _initialize_session(self):
        configuration = NSURLSessionConfiguration.defaultSessionConfiguration()
        self._delegate = _RequestsDelegate.alloc().initWithAdapter_(self)
        self._session = (
            NSURLSession.sessionWithConfiguration_delegate_delegateQueue_(
                configuration,
                self._delegate,
                None,
            )
        )

    def _receive_error(self, task, error):
        """
        Called by the delegate when a error has occurred.

        This call is expected only on background threads, and thus may not do
        anything that is not Python-thread-safe. This means that, for example,
        it is safe to grab things from the _tasks dictionary, but it is not
        safe to make other method calls on this object unless they explicitly
        state that they are safe in background threads.
        """
        queue, request = self._tasks[task]

        # TODO: Better exceptions!
        exception = Exception(error.localizedDescription)
        queue.put_nowait(exception)

    def _receive_response(self, task, response):
        """
        Called by the delegate when a response has been received.

        This call is expected only on background threads, and thus may not do
        anything that is not Python-thread-safe. This means that, for example,
        it is safe to grab things from the _tasks dictionary, but it is not
        safe to make other method calls on this object unless they explicitly
        state that they are safe in background threads.
        """
        queue, request = self._tasks[task]

        resp = Response()
        resp.status_code = getKey(response, 'statusCode')
        resp.reason = ''

        # TODO: Why do I have to do this?
        raw_headers = getKey(response, 'allHeaderFields')
        resp.headers = CaseInsensitiveDict(raw_headers)
        resp.encoding = get_encoding_from_headers(resp.headers)

        # TODO: This needs to point to an object that we can use to provide
        # the various raw things that requests needs.
        resp.raw = None

        if isinstance(request.url, bytes):
            resp.url = request.url.decode('utf-8')
        else:
            resp.url = request.url

        resp.request = request
        resp.connection = self

        # Put this response on the queue.
        queue.put_nowait(resp)


    def close(self):
        # TODO
        pass

    def send(self, request, stream=False, timeout=None, verify=True, cert=None,
             proxies=None):
        """
        Send a given request.
        """
        nsrequest = _build_NSRequest(request, timeout)

        # TODO: Support all of this stuff.
        assert not request.body
        assert not stream
        assert verify
        assert not cert
        assert not proxies

        # We need a queue to receive the response on.
        queue = Queue()
        task = self._session.dataTaskWithRequest_(nsrequest)
        self._tasks[task] = (queue, request)
        task.resume()

        response_or_error = queue.get()
        del self._tasks[task]

        if isinstance(response_or_error, Exception):
            raise response_or_error
        else:
            response = response_or_error

        return response
