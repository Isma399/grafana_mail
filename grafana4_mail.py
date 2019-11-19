#!/usr/bin/python
# coding: utf8
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.MIMEImage import MIMEImage
import smtplib
from datetime import datetime, date, time, timedelta
import requests
import shutil
import os

strFrom = 'grafana@<DOMAIN>'


def last_day():
    midnight = datetime.combine(date.today(), time.min)
    yesterday_mid = midnight - timedelta(days=1)
    epoch = datetime.utcfromtimestamp(0)
    midnight = midnight - timedelta(seconds=1)
    midnight = int((midnight - epoch).total_seconds() * 1000.0)
    yesterday_mid = int((yesterday_mid - epoch).total_seconds() * 1000.0)
    return str(yesterday_mid), str(midnight)


def download(panelId, begin_date, end_date):
    url = ('http://<GRAFANA_IP>:<PORT>/render/dashboard-solo/db/' +
           panelId[0] + 'from=' +
           begin_date + '&to=' + end_date + '&panelId=' + panelId[1] +
           '&width=1700&height=500'
           )
    print url
    r = requests.get(url, stream=True)
    if r.status_code == 200:
        with open('/tmp/img' + panelId[1] + '.png', 'wb') as picture:
            r.raw.decode_content = True
            shutil.copyfileobj(r.raw, picture)
    del r


def prepare():
    msgRoot = MIMEMultipart('related')
    msgRoot['Subject'] = '<SUBJECT>'
    msgRoot['From'] = strFrom
    msgRoot.preamble = 'This is a multi-part message in MIME format.'
    return msgRoot


def send(msgRoot, strTo):
    msgRoot['To'] = strTo
    smtp = smtplib.SMTP()
    smtp.connect('<MAILHOST>')
    smtp.sendmail(strFrom, strTo, msgRoot.as_string())
    smtp.quit()


def attach_img(msgRoot, panelId):
    fp = open('/tmp/img' + panelId + '.png', 'rb')
    msgImage = MIMEImage(fp.read())
    fp.close()
    msgImage.add_header('Content-ID', panelId)
    msgRoot.attach(msgImage)


if __name__ == '__main__':
    panelId_list = [('<PANEL_NAME>?', '<GRAPH_ID>'),
                    ('<PANEL_NAME>?', '<GRAPH_ID>'),
                   ]  
    for panelId in panelId_list:
        download(panelId, last_day()[0], last_day()[1])

    msgRoot = prepare()

    msgAlternative = MIMEMultipart('alternative')
    msgRoot.attach(msgAlternative)
    msgText = MIMEText('<TEXT>')
    msgAlternative.attach(msgText)

    msgStr = '<TEXT><br>'
    for panelId in panelId_list:
        msgStr += '<img src="cid:' + panelId[1] + '"><br>'
    msgText = MIMEText(msgStr, 'html')
    msgAlternative.attach(msgText)

    for panelId in panelId_list:
        attach_img(msgRoot, panelId[1])
    send(msgRoot, '<YOUR_MAIL_ADDRESS')
    send(msgRoot, '<MAIL_ADDRESS2>')

    for panelId in panelId_list:
        os.remove('/tmp/img' + panelId[1] + '.png')

