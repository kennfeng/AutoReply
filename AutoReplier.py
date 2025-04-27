import imaplib
import smtplib
import email
import time
import logging
from email.mime.text import MIMEText
from datetime import datetime, timedelta

IMAP_SERVER = 'imap.gmail.com'
SMTP_SERVER = 'smtp.gmail.com'
EMAIL_ACCOUNT = ''  # your email here
PASSWORD = ''    # your app password here
CHECK_INTERVAL = 5  # check emails every 5 seconds
AUTO_REPLY_MESSAGE = '''
Thank you for your email. I am currently away and will respond to your message when I return.

Best Regards,

'''
SUBJECT = 'Auto-Reply'

# logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('email_autoreplier.log'),
        logging.StreamHandler()
    ]
)

replied_to = set()

def is_no_reply(sender_email):
    no_reply_keywords = ['no-reply', 'noreply', 'donotreply', 'do-not-reply', 'automated', 'notification', 'alerts', 'system']
    return any(keyword in sender_email.lower() for keyword in no_reply_keywords)

def is_auto_reply(message):
    auto_reply_subjects = ['auto', 'automatic', 'reply', 'vacation', 'out of office', 'ooo', 'away']
    subject = message.get('Subject', '').lower()
    
    if any(keyword in subject for keyword in auto_reply_subjects):
        return True
    
    auto_reply_headers = [
        'Auto-Submitted',
        'X-Auto-Response-Suppress',
        'X-Autoreply',
        'X-Autorespond'
    ]
    
    for header in auto_reply_headers:
        if message.get(header):
            return True
            
    return False

def send_auto_reply(recipient, subject):
    try:
        server = smtplib.SMTP_SSL(SMTP_SERVER, 465)
        server.login(EMAIL_ACCOUNT, PASSWORD)
        
        msg = MIMEText(AUTO_REPLY_MESSAGE)
        
        msg['Subject'] = SUBJECT
        msg['From'] = EMAIL_ACCOUNT
        msg['To'] = recipient
        
        server.sendmail(EMAIL_ACCOUNT, recipient, msg.as_string())
        server.quit()
        
        logging.info(f'Auto-reply sent to: {recipient}')
        return True
    except Exception as e:
        logging.error(f'Failed to send auto-reply to {recipient}: {str(e)}')
        return False

def check_email():
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_ACCOUNT, PASSWORD)
        mail.select('inbox')
        
        status, data = mail.search(None, 'UNSEEN')
        mail_ids = data[0].split()
        
        if not mail_ids:
            logging.info('No new emails to process')
            mail.logout()
            return
            
        logging.info(f'Found {len(mail_ids)} unread emails')
        
        for num in mail_ids:
            try:
                status, data = mail.fetch(num, '(RFC822)')
                raw_email = data[0][1]
                message = email.message_from_bytes(raw_email)
                
                # extract sender and message ID
                sender_name, sender_email = email.utils.parseaddr(message['From'])
                message_id = message.get('Message-ID', '')
                subject = message.get('Subject', '(No Subject)')
                
                logging.info(f'Processing email from: {sender_email}, Subject: {subject}')
                
                # skip if already replied to this sender recently
                if sender_email in replied_to:
                    logging.info(f'Already replied to {sender_email} recently. Skipping.')
                    continue
                    
                # skip no-reply addresses
                if is_no_reply(sender_email):
                    logging.info(f'Skipping no-reply address: {sender_email}')
                    continue
                    
                # skip auto-reply messages
                if is_auto_reply(message):
                    logging.info(f'Skipping auto-reply message from: {sender_email}')
                    continue
                
                # skip own email address
                if sender_email == EMAIL_ACCOUNT:
                    logging.info('Skipping email from self')
                    continue
                    
                # send auto-reply
                if send_auto_reply(sender_email, subject):
                    replied_to.add(sender_email)
                
            except Exception as e:
                logging.error(f'Error processing email {num}: {str(e)}')
        
        mail.logout()
        
    except Exception as e:
        logging.error(f'Error checking emails: {str(e)}')

def clean_replied_to_cache():
    # clear the replied_to set every 24 hours
    global replied_to
    replied_to = set()
    logging.info('Cleared replied_to cache.')

def main():
    logging.info('Starting Auto-Reply')
    
    last_cache_clear = datetime.now()
    
    try:
        while True:
            check_email()
            
            if datetime.now() - last_cache_clear > timedelta(days=1):
                clean_replied_to_cache()
                last_cache_clear = datetime.now()
                
            logging.info(f'Sleeping for {CHECK_INTERVAL} seconds.')
            time.sleep(CHECK_INTERVAL)
            
    except KeyboardInterrupt:
        logging.info('Stopped')
    except Exception as e:
        logging.error(f'Service encountered an error: {str(e)}')

if __name__ == '__main__':
    main()