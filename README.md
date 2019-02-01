# grafana_mail
Send report with grafana pictures.
Require python module 'aiohttp'

Updated for Python 3.6 and Grafana 5.3.4

**Basic Usage**: Specify each panel in panel_list as a 3-tuple of (dashId, dashName, panelId)
`./grafana_mail.py -m mail1@domain.test mail2@domain.test -M mailhost.domain.test -G http://garfana.domain.test:3000 -T <Grafana API key> -P 123,dashboard1,1 234,dashboard2,14 345,dashboard4,1 456,dashboard6,2`

**Semi-shortcut**: Specify a dashboard as a 2-tuple of (dashId, dashName), then provide panel_list as a list of integer panelIds.  Assumes all panels are on same Dashboard
`./grafana_mail.py -m mail1@domain.test mail2@domain.test -M mailhost.domain.test -G http://garfana.domain.test:3000 -T <Grafana API key> -D 123,dashboard1 -P 1 14 1 2`

**More-shortcut**: Specify a dashboard simply by it's dashId (the `uid` when looking at a Dashboard's JSON definition, or the full (leading 0's) numeric part of the dashboard's URL).  Script fetches dashName and full list of panelIds
`./grafana_mail.py -m mail1@domain.test mail2@domain.test -M mailhost.domain.test -G http://garfana.domain.test:3000 -T <Grafana API key> -D 123 -P 1 14 1 2`

**Uber-shortcut**: Don't specify panel_list, but include at least a dashId.  Script will fetch all panels on dashboard
`./grafana_mail.py -m mail1@domain.test mail2@domain.test -M mailhost.domain.test -G http://garfana.domain.test:3000 -T <Grafana API key> -D 123`
