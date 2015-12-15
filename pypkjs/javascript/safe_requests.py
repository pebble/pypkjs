from __future__ import absolute_import
"""
This module contains overrides for various layers of requests/urllib3 to prevent
making connections to blocked IP ranges.
"""

__author__ = 'katharine'

import requests.packages.urllib3.connection
import requests.packages.urllib3.exceptions
import requests.packages.urllib3.connectionpool
import requests.packages.urllib3.poolmanager
import requests.packages.urllib3.util.connection
import requests.adapters
import requests.exceptions
import socket
from netaddr import IPNetwork, IPAddress

reserved_ip_blocks = [
    IPNetwork("0.0.0.0/8"),       # self
    IPNetwork("10.0.0.0/8"),      # RFC 1918
    IPNetwork("100.64.0.0/10"),   # NAT
    IPNetwork("127.0.0.0/8"),     # Loopback
    IPNetwork("169.254.0.0/16"),  # Link local
    IPNetwork("172.16.0.0/12"),   # RFC 1918
    IPNetwork("192.168.0.0/16"),  # RFC 1918
    IPNetwork("::1/128"),         # loopback
    IPNetwork("::ffff/96"),       # IPv4 mapped addresses
    IPNetwork("2001::/32"),       # teredo
    IPNetwork("2002::/16"),       # 6to4
    IPNetwork("fc00::/7"),        # local addresses
    IPNetwork("fe80::/10"),       # link-local
]


# This function is copied from util/connection.py in urllib3, which is embedded in
# requests, and in turn copied it from the python 2.7 library test suite.
# Added to its signature is only `socket_options`.
def create_connection_nonlocal(address, timeout=socket._GLOBAL_DEFAULT_TIMEOUT,
                      source_address=None, socket_options=None):
    """Connect to *address* and return the socket object.

    Convenience function.  Connect to *address* (a 2-tuple ``(host,
    port)``) and return the socket object.  Passing the optional
    *timeout* parameter will set the timeout on the socket instance
    before attempting to connect.  If no *timeout* is supplied, the
    global default timeout setting returned by :func:`getdefaulttimeout`
    is used.  If *source_address* is set it must be a tuple of (host, port)
    for the socket to bind as a source address before making the connection.
    An host of '' or port 0 tells the OS to use the default.
    """
    host, port = address
    err = None
    for res in socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM):
        af, socktype, proto, canonname, sa = res
        sock = None
        try:
            # Bail out if this is a reserved net.
            for network in reserved_ip_blocks:
                if IPAddress(sa[0]) in network:
                    raise requests.exceptions.RequestException("Illegal target host.")
            sock = socket.socket(af, socktype, proto)

            # If provided, set socket level options before connecting.
            # This is the only addition urllib3 makes to this function.
            requests.packages.urllib3.util.connection._set_socket_options(sock, socket_options)

            if timeout is not socket._GLOBAL_DEFAULT_TIMEOUT:
                sock.settimeout(timeout)
            if source_address:
                sock.bind(source_address)
            sock.connect(sa)
            return sock

        except socket.error as _:
            err = _
            if sock is not None:
                sock.close()

    if err is not None:
        raise err
    else:
        raise socket.error("getaddrinfo returns an empty list")


class NonlocalHTTPConnection(requests.packages.urllib3.connection.HTTPConnection):
    def _new_conn(self):
        """ Establish a socket connection and set nodelay settings on it.

        :return: New socket connection.
        """
        extra_kw = {}
        if self.source_address:
            extra_kw['source_address'] = self.source_address

        if self.socket_options:
            extra_kw['socket_options'] = self.socket_options

        try:
            conn = create_connection_nonlocal(
                (self.host, self.port), self.timeout, **extra_kw)

        except socket.timeout:
            raise requests.packages.urllib3.exceptions.ConnectTimeoutError(
                self, "Connection to %s timed out. (connect timeout=%s)" %
                (self.host, self.timeout))

        return conn


class NonlocalHTTPSConnection(requests.packages.urllib3.connection.HTTPSConnection, NonlocalHTTPConnection):
    pass


class NonlocalHTTPConnectionPool(requests.packages.urllib3.connectionpool.HTTPConnectionPool):
    ConnectionCls = NonlocalHTTPConnection


class NonlocalHTTPSConnectionPool(requests.packages.urllib3.connectionpool.HTTPSConnectionPool):
    ConnectionCls = NonlocalHTTPSConnection

pool_classes_by_scheme = {
    'http': NonlocalHTTPConnectionPool,
    'https': NonlocalHTTPSConnectionPool,
}


class NonlocalPoolManager(requests.packages.urllib3.poolmanager.PoolManager):
    def _new_pool(self, scheme, host, port):
        """
        Create a new :class:`ConnectionPool` based on host, port and scheme.

        This method is used to actually create the connection pools handed out
        by :meth:`connection_from_url` and companion methods. It is intended
        to be overridden for customization.
        """
        pool_cls = pool_classes_by_scheme[scheme]
        kwargs = self.connection_pool_kw
        if scheme == 'http':
            kwargs = self.connection_pool_kw.copy()
            for kw in requests.packages.urllib3.poolmanager.SSL_KEYWORDS:
                kwargs.pop(kw, None)

        return pool_cls(host, port, **kwargs)


class NonlocalHTTPAdapter(requests.adapters.HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=requests.adapters.DEFAULT_POOLBLOCK, **pool_kwargs):
        """Initializes a urllib3 PoolManager.

        This method should not be called from user code, and is only
        exposed for use when subclassing the
        :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`.

        :param connections: The number of urllib3 connection pools to cache.
        :param maxsize: The maximum number of connections to save in the pool.
        :param block: Block when no free connections are available.
        :param pool_kwargs: Extra keyword arguments used to initialize the Pool Manager.
        """
        # save these values for pickling
        self._pool_connections = connections
        self._pool_maxsize = maxsize
        self._pool_block = block

        self.poolmanager = NonlocalPoolManager(num_pools=connections, maxsize=maxsize,
                                       block=block, strict=True, **pool_kwargs)
