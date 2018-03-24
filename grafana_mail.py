#!/usr/bin/python
# coding: utf8
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.MIMEImage import MIMEImage
from email.utils import formatdate
import smtplib
from datetime import datetime, date, time, timedelta
import requests
import shutil
import os
import argparse
import socket
import re
import binascii

def mail_type(s):
    if not re.match(r"[^@^\s]+@[^@^\s]+\.[^@\s]+", s):
         raise argparse.ArgumentTypeError('The mail is not a valid email')
    return s       

def panel_type(s):
    try:
        x, panelId = s.split(',')
        try:
            y = int(panelId)
        except ValueError:
            print "PanelId must be an integer." 
        return x, panelId            
    except:
         #raise argparse.ArgumentTypeError("Every panel must be <str>dashboard,<int>panelId")
         print "Render complete dashboard."
    return s, None

def parse_args():
    parser = argparse.ArgumentParser(
        description='Return aliases of all the subscribers of a list.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-f", "--mail_from",
                    dest="mail_from",
                    help="Mail from address.",
                    required=False)
    parser.add_argument("-m", "--mail_list",
                    dest="mail_list",
                    nargs='+', type=mail_type,
                    help="Mail list, separed by space.",
                    required=True)
    parser.add_argument("-M", "--mailhost",
                    dest="mailhost", type=str,
                    help="Mailhost hostname or IP or just in simple: localhost",
                    required=True)
    parser.add_argument("-G", "--grafana_server",
                    dest="grafana_server",
                    help="Grafana server & port, ex: http://grafana.test:3000 or http://localhost:3000",
                    required=True)
    parser.add_argument("-P", "--panel_list",
                    dest="panel_list",
                    nargs='+', type=panel_type,
                    help="Tuple of Grafana dashboard Id and panelId, every tuple has to be separated by a space, ex ('test', 1) ('dashboard2', 15) ...",
                    required=True)   
    parser.add_argument("-T", "--api_token",
                    dest="api_token", type=str,
                    help="Grafana API Token to access the dashboard.",
                    required=True)
    parser.add_argument("-W", "--img_width",
                    dest="img_width", type=str,
                    help="Width size of image.",
                    required=True)
    parser.add_argument("-H", "--img_height",
                    dest="img_height", type=str,
                    help="Height size of image.",
                    required=True)
        return parser.parse_args()

def last_day():
    midnight = datetime.combine(date.today(), time.min)
    yesterday_mid = midnight - timedelta(days=1)
    epoch = datetime.utcfromtimestamp(0)
    midnight = midnight - timedelta(seconds=1)
    midnight = int((midnight - epoch).total_seconds() * 1000.0)
    yesterday_mid = int((yesterday_mid - epoch).total_seconds() * 1000.0)
    return str(yesterday_mid), str(midnight)

def download(panelId, begin_date, end_date, grafana_server, api_token, img_width, img_height):
    if panelId[1] == None:
        url = (grafana_server + '/render/dashboard/db/' +
               panelId[0] + '?from=' +
               begin_date + '&to=' + end_date +
               '&width=' + img_width + '&height=' + img_height
               )
    else:
        url = (grafana_server + '/render/dashboard-solo/db/' +
               panelId[0] + '?from=' +
               begin_date + '&to=' + end_date + '&panelId=' + panelId[1] +
               '&width=' + img_width + '&height=' + img_height
               )
    print url
    r = requests.get(url, headers={"Authorization": "Bearer " + api_token}, stream=True)
    if r.status_code == 200:
        if panelId[1] == None:
            img_file = 'img_' + panelId[0] + '.png'
        else:
            img_file = 'img_' + panelId[0] + '-' + panelId[1] + '.png'
        with open('./' + img_file, 'wb') as picture:
            r.raw.decode_content = True
            shutil.copyfileobj(r.raw, picture)
    del r

def prepare():
    msgRoot = MIMEMultipart('related')
    msgRoot['Subject'] = 'Grafana Reports.'
    msgRoot['From'] = '<' + strFrom + '>'
    msgRoot['Date'] = formatdate()
    msgRoot['Message-ID'] = '<' + binascii.b2a_hex(os.urandom(15)) + '@' + strFrom + '>'
    print msgRoot['Message-ID']
    msgRoot.preamble = 'This is a multi-part message in MIME format.'
    return msgRoot

def send(msgRoot, strTo, mailhost):
    msgRoot['To'] = '<' + strTo + '>'
    smtp = smtplib.SMTP()
    smtp.connect(mailhost)
    smtp.sendmail(strFrom, strTo, msgRoot.as_string())
    smtp.quit()

def attach_img(msgRoot, panelId, dashboard):
    global msgStr
    if panelId == None:
        img_name = 'img_' + dashboard
    else:
        img_name = 'img_' + dashboard + '-' + panelId
    fp = open('./' + img_name + '.png', 'rb')
    msgImage = MIMEImage(fp.read(), _subtype="png")
    fp.close()
    #for panelId in args.panel_list:
    #    msgStr += '<img src="cid:' + img_name + '"><br>'
    msgImage.add_header('Content-ID', '<' + img_name + '>')
    msgImage.add_header('Content-Disposition', 'attachment;filename="' + img_name + '.png"')
    msgRoot.attach(msgImage)

if __name__ == '__main__':
    args = parse_args()
    if args.mail_from:
        strFrom = args.mail_from
    else:
        strFrom = socket.getfqdn()
     
    for panelId in args.panel_list:
        download(panelId, last_day()[0], last_day()[1], args.grafana_server, args.api_token, args.img_width, args.img_height)
    msgRoot = prepare()

    msgStr = """
Hi,

This is Grafana Mail.

"""
    msgAlternative = MIMEMultipart('alternative')
    msgRoot.attach(msgAlternative)
    msgText = MIMEText(msgStr)
    msgAlternative.attach(msgText)

    for panelId in args.panel_list:
        if panelId[1] == None:
            img_name = 'img_' + panelId[0]
        else:
            img_name = 'img_' + panelId[0] + '-' + panelId[1]
        msgStr += '<img src="cid:' + img_name + '"> '
    msgText = MIMEText(msgStr.replace('\n', '<br />'), 'html')
    msgAlternative.attach(msgText)

    for panelId in args.panel_list:
        attach_img(msgRoot, panelId[1], panelId[0])
    
    for mail in args.mail_list:
        send(msgRoot, mail, args.mailhost)

    for panelId in args.panel_list:
        if panelId[1] == None:
            img_name = 'img_' + panelId[0]
        else:
            img_name = 'img_' + panelId[0] + '-' + panelId[1]
        os.remove('./' + img_name + '.png')

