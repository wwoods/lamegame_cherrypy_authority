
class Registrar(object):
    def __init__(self, conf):
        """Initializes a new registrar with the given params."""
        self.conf = conf

    def new_account_ok(self, uname, redirect):
        """Get a message detailing the user's next step"""
        raise NotImplementedError()

    def new_user_fields(self, **kwargs):
        """Returns fields (in a table row of name: input format) required
        for registration.

        kwargs -- Dict of known attributes from e.g. the last try at creating
            a new account or an OpenID authentication.
        """

    def process_new_user(self, uname, uargs, authargs, redirect):
        """Process the holder record for new user uname.  
        On success, either config.auth.user_create_holder or 
        config.auth.user_create should be called.

        authargs is the POST variables for the new account
        request.
        """
        raise NotImplementedError()

    def response_link(self, **kwargs):
        """Respond to a link crafted by this registrar for this registrar."""
        raise NotImplementedError()

