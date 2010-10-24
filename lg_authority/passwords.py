"""A collection of password hashing methods, if needed.  Each algorithm
should take a password and a salt_or_compare argument, that is either
a string (salt) or a list that represents the hashed password and 
the salt used to get that hash.

If salt_or_compare is a previously hashed password pair, then the
functions should return True or False.  Otherwise, they should
return a hashed password pair.
"""

from .common import *

from hashlib import sha256 as _sha256
import hmac

def check_complexity(password):
    """Checks the password.  Returns a human-readable reason for the
    password to not be used, or None if the password is ok.
    """

    if len(password) < 6:
        return "Password must be at least 6 characters long"
    return None

def sha256(password, salt_or_compare=None):
    """Returns a password that is salted and hashed with sha256, or
    returns True or False if salt_or_compare is a 2-item list.
    """
    if type(salt_or_compare) == list:
        if len(salt_or_compare) != 2:
            raise ValueError("salt_or_compare must be a 2-element list")
        salt = salt_or_compare[1]
    else:
        salt = salt_or_compare

    if salt is None:
        import uuid
        salt = uuid.uuid4().hex

    combined = password + salt

    hashed = hmac.new(
        combined.encode('utf-8')
        , config['site_key'].encode('utf-8')
        , _sha256
        ).hexdigest()
    result = [ hashed, salt ]

    if type(salt_or_compare) == list:
        if salt_or_compare == result:
            return True
        return False
    return result

def verify(password, record):
    """Returns True if password matches record.  record is a (type, hash) 
    tuple.
    """

    type = record[0]
    passwd = record[1]
    
    if globals().get(type, lambda u,h: False)(password, passwd):
        return True
    return False

