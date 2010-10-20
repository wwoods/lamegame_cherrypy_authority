from .common import *

from hashlib import sha256 as _sha256
import hmac

def sha256(password, salt=None):
    """Returns a password that is salted and hashed with sha256"""
    if salt is None:
        import uuid
        salt = uuid.uuid4().hex

    combined = password + salt

    hashed = hmac.new(
        combined.encode('utf-8')
        , config['site_key'].encode('utf-8')
        , _sha256
        ).hexdigest()
    return [ hashed, salt ]

