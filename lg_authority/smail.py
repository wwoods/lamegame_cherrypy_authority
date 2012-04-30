#Email module that uses config['site_email'] to send mail to users.

from .common import *

def send_mail(to, subject, body, frm=None):
    """Sends an e-mail to "to" with subject "subject" and body "body".
    "frm" may optionally be specified to send as under a different account
    than the default.
    """
    conf = config['site_email']
    if conf is None:
        raise RuntimeError('send_mail() called, but no site_email provided')

    frm = frm or config['site_email']['default']

    import smtplib
    from email.mime.text import MIMEText

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = frm
    msg['To'] = to

    server = conf.get('smtpserver')
    port = conf.get('smtpport') or 25
    use_ssl = conf.get('smtpssl')
    if use_ssl:
        s = smtplib.SMTP_SSL(server, port)
    else:
        s = smtplib.SMTP(server, port)
    user = conf.get('smtpuser')
    if user:
        password = conf.get('smtppass')
        s.login(user, password)
    try:
        s.sendmail(frm, to, msg.as_string())
    finally:
        s.quit()

