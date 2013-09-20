#!/usr/bin/env python
# coding:utf-8

import _env
import conf.private.email as config_email
# config_email.SMTP
# config_email.SMTP_USERNAME
# config_email.SMTP_PASSWORD
# config_email.SENDER_MAIL
# config_email.ALARM_ADDRESS

from email.MIMEText import MIMEText
from email.Header import Header
from email.Utils import formataddr
import smtplib
from lib.job_queue import Job

import socket

class AlarmJob(Job):
    
    def __init__(self, email_alarm, subject, body=""):
        Job.__init__(self)
        self.email_alarm = email_alarm
        self.subject = subject
        self.body = body

    def do(self):
        self.email_alarm.send(self.subject, self.body)


class EmailAlarm(object):

    def __init__(self, logger):
        self.address_list = config_email.ALARM_ADDRESS
        assert isinstance(self.address_list, (tuple, list, set))
        self.logger = logger

    def send(self, subject, body):
        try:
            server = smtplib.SMTP(config_email.SMTP, config_email.SMTP_PORT)
            server.ehlo()
            server.esmtp_features['auth'] = 'LOGIN PLAIN'
            if config_email.SMTP != 'localhost':
                server.login(config_email.SMTP_USERNAME, config_email.SMTP_PASSWORD)

            enc = 'utf-8'
            format = 'plain'
            msg = MIMEText(body, format, enc)
            msg['Subject'] = Header(subject, enc)

            #sender_name = str(Header(sender_name, enc))
            #msg['From'] = formataddr((sender_name, sender))
            msg['From'] = config_email.SENDER_MAIL

            #recipient_name = str(Header(recipient_name, enc))
            #msg['To'] = formataddr((recipient_name, recipient))
            recipient = ",".join(self.address_list)
            msg['To'] = recipient

            server.sendmail(config_email.SENDER_MAIL, recipient, msg.as_string())
            self.logger.info("sent %s " %  (subject))
        except Exception, e:
            self.logger.exception(e)
            self.logger.error("cannot send %s " %  (subject))

        

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :
