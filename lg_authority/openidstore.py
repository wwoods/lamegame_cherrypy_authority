from .common import *

try:
    import openid
except ImportError:
    pass #Do nothing!
else:
    from openid.store import nonce
    import copy
    import time

    Slate = config.Slate

    class OpenIdStore(object):
        """Uses Slates to handle openid authentication"""

        ns = "openid" #The section to store data in.
        server_timeout = 600 #seconds until we forget about a server and its
                             #associations.
        assocs = "a-"
        nonces = "n-"

        def __init__(self, section):
            self.ns = section

        def _getassocs(self, server_url):
            return Slate(self.ns, self.assocs + server_url, self.server_timeout)

        def storeAssociation(self, server_url, assoc):
            a = self._getassocs(server_url)
            a[assoc.handle] = assoc

        def getAssociation(self, server_url, handle=None):
            a = self._getassocs(server_url)
            result = None
            if handle is None:
                best = None
                for val in a.values():
                    if best is None or best.issued < val.issued:
                        best = val
                result = best
            else:
                result = a[handle]
            if result is not None and result.getExpiresIn() == 0:
                result = None
            return result

        def removeAssociation(self, server_url, handle):
            a = self._getassocs(server_url)
            try:
                del a[handle]
            except KeyError:
                return False
            else:
                return True

        def useNonce(self, server_url, timestamp, salt):
            if abs(timestamp - time.time()) > nonce.SKEW:
                log('OpenID nonce denied')
                return False

            anonce = str((str(server_url), int(timestamp), str(salt)))
            snonce = Slate(self.ns, self.nonces + anonce, nonce.SKEW)
            if not snonce.is_expired():
                return False
            else:
                snonce.touch()
                return True

