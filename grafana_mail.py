#!/usr/bin/python
# coding: utf8

"""
Updated for Python 3.6 and Grafana 5.3.4

Basic Usage: Specify each panel in panel_list as a 3-tuple of (dashId, dashName, panelId)
./grafana_mail.py -m mail1@domain.test mail2@domain.test -M mailhost.domain.test -G http://garfana.domain.test:3000 -T <Grafana API key> -P 123,dashboard1,1 234,dashboard2,14 345,dashboard4,1 456,dashboard6,2

Semi-shortcut: Specify a dashboard as a 2-tuple of (dashId, dashName), then provide panel_list as a list of integer panelIds.  Assumes all panels are on same Dashboard
./grafana_mail.py -m mail1@domain.test mail2@domain.test -M mailhost.domain.test -G http://garfana.domain.test:3000 -T <Grafana API key> -D 123,dashboard1 -P 1 14 1 2

More-shortcut: Specify a dashboard simply by it's dashId (the `uid` when looking at a Dashboard's JSON definition, or the full (leading 0's) numeric part of the dashboard's URL).  Script fetches dashName and full list of panelIds
./grafana_mail.py -m mail1@domain.test mail2@domain.test -M mailhost.domain.test -G http://garfana.domain.test:3000 -T <Grafana API key> -D 123 -P 1 14 1 2

Uber-shortcut: Don't specify panel_list, but include at least a dashId.  Script will fetch all panels on dashboard
./grafana_mail.py -m mail1@domain.test mail2@domain.test -M mailhost.domain.test -G http://garfana.domain.test:3000 -T <Grafana API key> -D 123
"""

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

from email.utils import formatdate
import smtplib
from datetime import datetime, date, time, timedelta
import requests

import os
import argparse
import socket
import re
import binascii
# Import Async HTTP libs for fetching graphics
import asyncio
import aiohttp



# TODO support asynchttp fetching of graphs for speed

def mail_type(s):
    if not re.match(r"[^@^\s]+@[^@^\s]+\.[^@\s]+", s):
        raise argparse.ArgumentTypeError('The mail is not a valid email')
    return s


def dashboard_type(s):
    """ A dash can include the Dashboard Name (slug) or not.  If just the Dashboard ID (uid) is provided, then no
     Panels need to be provided - it will fetch full list of panels and download images for all of them. """
    try:
        dashId, dashName = s.split(',')

        try:
            int(dashId)
        except ValueError:
            print("DashId must be an integer.")
        return dashId, dashName
    except:
        # raise argparse.ArgumentTypeError("Every panel must be <str>dashboard,<int>panelId")
        print(f"Render complete dashboard with UID {s}")
        return s, None


def panel_type(s):
    try:
        splits = s.split(',')
        if len(splits) == 3:
            dashId, dashName, panelId = splits
            try:
                int(dashId)
            except ValueError:
                print("DashId must be an integer.")
            try:
                int(panelId)
            except ValueError:
                print("PanelId must be an integer.")
            return dashId, dashName, panelId
        elif len(splits) == 1:
            # Assume dashboard arg is provided
            try:
                int(s)
            except ValueError:
                print("PanelId must be an integer.")
    except:
        # raise argparse.ArgumentTypeError("Every panel must be <str>dashboard,<int>panelId")
        print("Render complete dashboard.")
    return s


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
                        help="Mailhost hostname or IP.",
                        required=True)
    parser.add_argument("-G", "--grafana_server",
                        dest="grafana_server",
                        help="Grafana server & port, ex: http://grafana.test:3000",
                        required=True)
    parser.add_argument("-D", "--dashboard",
                        dest="dashboard",
                        type=dashboard_type,
                        help="Tuple of Grafana `dashboardID,dashboardName` or simply the ID (autodetects dashboardName).  If provided, `panel_list` should just be a list string of integer PanelIDs ex `1 3 4 7`",
                        required=False)
    parser.add_argument("-P", "--panel_list",
                        dest="panel_list",
                        nargs='+', type=panel_type,
                        help="Tuple of Grafana (dashboardId, dashboardName and panelId), every tuple has to be separated by a space, ex `00123,test-dashboard,1 00987,dashboard2,15 ...`.  If `dashboard` provided, can omit `panel-list` to dowload all panels in dash")
    parser.add_argument("-T", "--api_token",
                        dest="api_token", type=str,
                        help="Grafana API Token to access the dashboard.",
                        required=True)
    return parser.parse_args()


def last_day():
    """ Calculates last day of data avaialbility, which is ~2 days ago"""
    midnight = datetime.combine(date.today(), time.min) - timedelta(days=2)
    yesterday_mid = midnight - timedelta(days=30)
    epoch = datetime.utcfromtimestamp(0)
    midnight = midnight - timedelta(seconds=1)
    midnight = int((midnight - epoch).total_seconds() * 1000.0)
    yesterday_mid = int((yesterday_mid - epoch).total_seconds() * 1000.0)
    return str(yesterday_mid), str(midnight)



async def download_async(session, panel, begin_date, end_date, grafana_server, api_token):
    url = f"{grafana_server}/render/d-solo/{panel[0]}/{panel[1]}?panelId={panel[2]}&from={begin_date}&to={end_date}&width=1000&height=500"
    async with session.get(url, headers={"Authorization": "Bearer " + api_token}) as resp:
        if resp.status == 200:
            img_file = 'img_' + panel[1] + '-' + panel[2] + '.png'
            with open(img_file, 'wb') as fd:
                while True:
                    chunk = await resp.content.read(10000)
                    if not chunk:
                        break
                    fd.write(chunk)


async def download_all_async(panels, begin_date, end_date, grafana_server, api_token):
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(verify_ssl=False)) as session:
        tasks = [download_async(session, panel, begin_date, end_date, grafana_server, api_token) for panel in panels]
        return await asyncio.gather(*tasks)


def prepare():
    msgRoot = MIMEMultipart('related')
    msgRoot['Subject'] = ' Grafana Report'
    msgRoot['From'] = '<' + strFrom + '>'
    msgRoot['Date'] = formatdate()
    msgRoot['Message-ID'] = f"<{str(binascii.b2a_hex(os.urandom(15)))}@{strFrom}>"
    # print(msgRoot['Message-ID'])
    msgRoot.preamble = 'This is a multi-part message in MIME format.'
    return msgRoot


def send(msgRoot, strTo, mailhost):
    msgRoot['To'] = '<' + strTo + '>'
    smtp = smtplib.SMTP(mailhost)
    # smtp.connect(mailhost)
    smtp.sendmail(strFrom, strTo, msgRoot.as_string())
    smtp.quit()


def attach_img(msgRoot, img_name):
    global msgStr
    # img_name = 'img_' + dashboardName + '-' + panelId
    fp = open('./' + img_name + '.png', 'rb')
    msgImage = MIMEImage(fp.read(), _subtype="png")
    fp.close()
    # for panelId in args.panel_list:
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

    # Determine timeframe to fetch for
    from_epoch, to_epoch = last_day()

    # Re-form panel_list arg base on if dashboard is provided
    if args.dashboard:

        d = args.dashboard
        # If user didn't supply dash slug, then we need to fetch the dash description
        if d[1] is None or not args.panel_list:
            dash_json = requests.get(f"{args.grafana_server}/api/dashboards/uid/{d[0]}",
                                     headers={"Authorization": "Bearer " + args.api_token}).json()
            # Set the dash slug in our tuple
            d = (d[0], dash_json['meta']['slug'])

            # Also, if there's no panel_list, then make one of all panel IDs in `dash_json`
            if not args.panel_list:
                args.panel_list = [str(p['id']) for p in dash_json['dashboard']['panels']]
                print(f"Getting all panels from dashboard {d}: {args.panel_list}")

        args.panel_list = [(d[0], d[1], p) for p in args.panel_list]

    # Use async code instead
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(download_all_async(args.panel_list, from_epoch, to_epoch, args.grafana_server, args.api_token))

    msgRoot = prepare()

    msgStr = """
<h3>Grafana Report</h3>

This is the daily snapshot of the latest Grafana graphs.

Best Regards,
Grafana Team
"""
    msgAlternative = MIMEMultipart('alternative')
    msgRoot.attach(msgAlternative)
    msgText = MIMEText(msgStr)
    msgAlternative.attach(msgText)

    # Each panelId is a 3-tuple of (DashID, DashName, PanelID)
    image_names = [f"img_{panel[1]}-{panel[2]}" for panel in args.panel_list]

    for img_name in image_names:
        # img_name = 'img_' + panel[1] + '-' + panel[2]
        msgStr += '<img src="cid:' + img_name + '"><br>'
    msgText = MIMEText(msgStr.replace('\n', '<br />'), 'html')
    msgAlternative.attach(msgText)

    # for panel in args.panel_list:
    for img_name in image_names:
        attach_img(msgRoot, img_name)

    for mail in args.mail_list:
        send(msgRoot, mail, args.mailhost)

    # for panel in args.panel_list:
    for img_name in image_names:
        # img_name = 'img_' + panel[1] + '-' + panel[2]
        os.remove('./' + img_name + '.png')
