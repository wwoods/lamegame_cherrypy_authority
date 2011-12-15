
import datetime
from hashlib import sha256
from uuid import uuid4
from lg_authority.common import AuthError, config

class AuthToken:
    """Utility methods for dealing with AuthTokens.
    """

    @classmethod
    def create(cls, userId, userName, days):
        """Creates an authtoken valid for the given number of days.
        """
        token = {
            'name': userName
            ,'id': userId
            ,'uuid': uuid4().hex
            ,'expiration': (
                datetime.datetime.utcnow() + datetime.timedelta(days=days)
                ).isoformat() + 'Z'
        }
        token['hash'] = cls._getHash(token)
        return cls._urlencode(token)

    @classmethod
    def isExpired(cls, authToken):
        """Returns True if the given authToken is expired.
        """
        parts = cls._urldecode(authToken)
        cls._validate(parts)
        expiry = cls._decodeDate(parts['expiration'])
        if datetime.datetime.utcnow() >= expiry:
            return True
        return False

    @classmethod
    def isTooRecentForNew(cls, authToken):
        """Returns True if the given authToken is not expired and is too
        recent for a new token to be generated (more recent than 90 days).
        """
        parts = cls._urldecode(authToken)
        expiry = cls._decodeDate(parts['expiration'])
        expiry -= datetime.timedelta(days=90)
        if datetime.datetime.utcnow() < expiry:
            return True
        return False

    @classmethod
    def _decodeDate(cls, date):
        """Decodes an ISO format (+Z timezone) date to a utc datetime object.
        """
        return datetime.datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.%fZ")

    @classmethod
    def _getHash(cls, token):
        """Returns the hash for a given token dict.  The token dict may include
        the hash element; it will not be included.
        """
        hash = sha256(config['site_key'])
        for key,val in sorted(token.items()):
            if key == 'hash':
                continue
            hash.update(str(key) + ':' + str(val))
        return hash.hexdigest()

    @classmethod
    def _urldecode(cls, args):
        """Turns a url string like a=1&b=2 into a dict.
        """
        parts = args.split('|')
        decoded = {}
        for p in parts:
            pp = p.split(':', 1)
            decoded[pp[0]] = pp[1]
        return decoded

    @classmethod
    def _urlencode(cls, args):
        """Turns a dict into a url friendly string.
        """
        parts = []
        for key,val in sorted(
            args.items()
            , key=lambda a: 'zzz' if a[0] == 'hash' else a[0]
            ):
            parts.append(key + ':' + val)
        return '|'.join(parts)

    @classmethod
    def _validate(cls, token):
        """Validates a token dict.  Essentially, the sha256 part should equal
        the sha for all of the other parts.

        Raises an AuthError on failure.
        """
        newHash = cls._getHash(token)
        if newHash != token['hash']:
            raise AuthError("Invalid AuthToken")


