import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from os.path import expanduser, join



def send_mail(content, from_, to, *files, **other):
    """send_mail('Nice day !', from_='me@hmail.com', to='notme@kmail.com',
               subject='important', reply_to='trash@dustbin.org')"""


    join(expanduser('~'), '.config', 'ptyx')

    msg = MIMEMultipart()
    msg['from'] = from_
    msg['to'] = to
    for name in headers:
        msg[name.replace('_', '-')] = headers[name]
    msg.attach(MIMEText(content))

    # Attach files.
    for file_name in files:
        with open(file_name, "rb") as f:
            part = MIMEApplication(f.read(), name=basename(f))
        # After the file is closed
        part['Content-Disposition'] = 'attachment; filename="%s"' % basename(f)
        msg.attach(part)

    mailserver = smtplib.SMTP('smtp.gmail.com', 587)
    mailserver.ehlo()
    mailserver.starttls()
    mailserver.ehlo()
    mailserver.login('XXX@gmail.com', 'PASSWORD')
    mailserver.sendmail(from_, to, msg.as_string())
    mailserver.quit()
