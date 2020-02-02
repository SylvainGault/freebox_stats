#!/usr/bin/env python3

import re
import collections
import argparse
import datetime
import requests
import config
import db


class StatsPage(object):
    def __init__(self, url=None):
        if url is None:
            url = config.statsurl

        self.url = url
        self._content = None
        self._sections = None
        self._uptime = None
        self._adsl_state = None
        self._cnx_events = None
        self._links = None

    @property
    def content(self):
        if self._content is not None:
            return self._content

        res = requests.get(self.url, timeout=60*60)
        res.raise_for_status()
        self._content = res.text
        return self._content

    @property
    def sections(self):
        if self._sections is not None:
            return self._sections

        sectionsre = re.compile(r'(.*?)(?: :)?\n=+\n((?:.*(?:\n|$)(?!=))*)')
        sec = collections.OrderedDict(sectionsre.findall(self.content))
        self._sections = sec
        return self._sections

    @property
    def uptime(self):
        if self._uptime is not None:
            return self._uptime

        infocontent = self.sections['Informations générales']
        bootupre = re.compile('Temps depuis la mise en route\s*(?:(\d+) jours?,)?\s*(?:(\d+) heures?,)?\s*(\d+) minutes?')
        match = bootupre.search(infocontent)
        days, hours, minutes = match.groups()

        days = 0 if days is None else int(days)
        hours = 0 if hours is None else int(hours)
        minutes = int(minutes)

        self._uptime = datetime.timedelta(days=days, hours=hours, minutes=minutes)
        return self._uptime

    @property
    def bootup_date(self):
        """ The bootup time of the freebox in UTC timezone. """
        now = datetime.datetime.now(datetime.timezone.utc)
        return now - self.uptime

    @property
    def adsl_state(self):
        if self._adsl_state is not None:
            return self._adsl_state

        adslcontent = self.sections['Adsl']
        atmbwre = re.compile(r'Débit ATM\s+(\S+)\s*(\S+)\s+(\S+)\s*(\S+)')
        noisere = re.compile(r'Marge de bruit\s+(\S+)\s*(\S+)\s+(\S+)\s*(\S+)')
        attre = re.compile(r'Atténuation\s+(\S+)\s*(\S+)\s+(\S+)\s*(\S+)')
        fecre = re.compile(r'FEC\s+(\S+)\s+(\S+)')
        crcre = re.compile(r'CRC\s+(\S+)\s+(\S+)')
        hecre = re.compile(r'HEC\s+(\S+)\s+(\S+)')

        matmbw = atmbwre.search(adslcontent)
        mnoise = noisere.search(adslcontent)
        matt = attre.search(adslcontent)
        mfec = fecre.search(adslcontent)
        mcrc = crcre.search(adslcontent)
        mhec = hecre.search(adslcontent)

        atm_bw_down, unit_down, atm_bw_up, unit_up = matmbw.groups()
        if unit_down != 'kb/s':
            raise ValueError("Unknown ATM bandwidth unit: " + unit_down)
        if unit_up != 'kb/s':
            raise ValueError("Unknown ATM bandwidth unit: " + unit_up)

        noise_margin_down, unit_down, noise_margin_up, unit_up = mnoise.groups()
        if unit_down != 'dB':
            raise ValueError("Unknown noise margin unit: " + unit_down)
        if unit_up != 'dB':
            raise ValueError("Unknown noise margin unit: " + unit_up)

        att_down, unit_down, att_up, unit_up = matt.groups()
        if unit_down != 'dB':
            raise ValueError("Unknown attenuation unit: " + unit_down)
        if unit_up != 'dB':
            raise ValueError("Unknown attenuation unit: " + unit_up)

        fec_down, fec_up = mfec.groups()
        crc_down, crc_up = mcrc.groups()
        hec_down, hec_up = mhec.groups()

        state = {}
        state['atm_bw_down'] = int(atm_bw_down)
        state['atm_bw_up'] = int(atm_bw_up)
        state['noise_margin_down'] = float(noise_margin_down)
        state['noise_margin_up'] = float(noise_margin_up)
        state['att_down'] = float(att_down)
        state['att_up'] = float(att_up)
        state['fec_down'] = int(fec_down)
        state['fec_up'] = int(fec_up)
        state['crc_down'] = int(crc_down)
        state['crc_up'] = int(crc_up)
        state['hec_down'] = int(hec_down)
        state['hec_up'] = int(hec_up)

        self._adsl_state = state
        return self._adsl_state

    @property
    def connection_events(self):
        if self._cnx_events is not None:
            return self._cnx_events

        adslcontent = self.sections['Adsl']

        eventre = re.compile(r'(?:(\d+/\d+/\d+ à \d+:\d+:\d+)|Mise en route)\s+(\S+)(?:\s+(\d+)\s*/\s*(\d+))?\s*\n')
        self._cnx_events = []
        matches = eventre.finditer(adslcontent)
        for m in reversed(list(matches)):
            date, event, bw_down, bw_up = m.groups()
            bootup = date is None
            if not bootup:
                date = datetime.datetime.strptime(date, "%d/%m/%Y à %H:%M:%S")
                date = date.astimezone(datetime.timezone.utc)
            else:
                date = self.bootup_date

            if event == "Connexion":
                event = "CONN"
            elif event == "Déconnexion":
                event = "DECO"
            else:
                raise ValueError("Unknown log event " + event)

            bw_down = bw_down if bw_down is None else int(bw_down)
            bw_up = bw_up if bw_up is None else int(bw_up)
            self._cnx_events.append((date, bootup, event, bw_down, bw_up))

        self._cnx_events.reverse()
        return self._cnx_events

    @property
    def links(self):
        if self._links is not None:
            return self._links

        netcontent = self.sections['Réseau']

        wanre = re.compile(r'WAN\s+(Ok|Non connecté)\s+(\d+)\s*(\S+)\s+(\d+)\s*(\S+)\s*\n')
        mwan = wanre.search(netcontent)

        wan_state, wan_down, unit_down, wan_up, unit_up = mwan.groups()
        if unit_down != 'ko/s':
            raise ValueError("Unknown WAN bandwidth unit: " + unit_down)
        if unit_up != 'ko/s':
            raise ValueError("Unknown WAN bandwidth unit: " + unit_up)

        wan_down = int(wan_down)
        wan_up = int(wan_up)

        self._links = [('WAN', wan_state, wan_down, wan_up)]
        return self._links



def store_stats(page, cur):
    """ Store the ADSL line statistics. """

    # Hopefully, the keys of the dict in page.adsl_state are also the names of
    # the fields of the table adsl_state.
    fields = ['atm_bw_down', 'atm_bw_up',
            'noise_margin_down', 'noise_margin_up',
            'att_down', 'att_up',
            'fec_down', 'fec_up',
            'crc_down', 'crc_up',
            'hec_down', 'hec_up']
    sqlfields = ", ".join(fields)
    sqlqm = ", ".join(["?"] * len(fields))

    values = tuple(page.adsl_state[f] for f in fields)
    cur.execute("""INSERT INTO adsl_state
            (date, %s)
            VALUES (datetime('now'), %s)""" % (sqlfields, sqlqm), values)



def store_logs(page, cur):
    """ Store the ADSL line connection event logs. """

    if len(page.connection_events) == 0:
        raise ValueError("No connection event log")

    # Fetch the last date so we don't re-insert the log entries
    cur.execute("SELECT MAX(date) FROM adsl_connection")
    lastdate, = cur.fetchone()
    if lastdate is None:
        # Set the lastdate unreasonably far in the past if it is not defined
        lastdate = datetime.datetime(1970, 1, 1)
    else:
        lastdate = datetime.datetime.fromisoformat(lastdate)

    if lastdate.tzinfo is None:
        lastdate = lastdate.replace(tzinfo=datetime.timezone.utc)

    # Store the ADSL connection log entries
    for date, isbootup, event, down, up in page.connection_events:
        cmpdate = date - datetime.timedelta(minutes=1) if isbootup else date
        if lastdate >= cmpdate:
            continue

        cur.execute("""INSERT INTO adsl_connection
                (date, isbootup, event, bw_down, bw_up)
                VALUES (?, ?, ?, ?, ?)""", (date, isbootup, event, down, up))



def store_netlinks(page, cur):
    """ Store the state of the network links. """

    if len(page.links) == 0:
        raise ValueError("No link state")

    for link, state, down, up in page.links:
        cur.execute("""INSERT INTO netlinks
                (date, link, state, usage_down, usage_up)
                VALUES (datetime('now'), ?, ?, ?, ?)""", (link, state, down, up))



def main():
    parser = argparse.ArgumentParser(description="Retrieve freebox statistics")
    parser.add_argument("-d", "--database", help="Sqlite3 database where to store the statistics (default: %s)" % config.database)
    parser.add_argument("-u", "--url", help="URL where the statistics are retrieved (default: %s)" % config.statsurl)

    args = parser.parse_args()

    if args.database is not None:
        config.database = args.database
    if args.url is not None:
        config.statsurl = args.url

    cnx = db.new_connection()
    cur = cnx.cursor()
    db.create_tables(cur)

    p = StatsPage()
    store_stats(p, cur)
    store_logs(p, cur)
    store_netlinks(p, cur)


    cur.execute("PRAGMA optimize")
    cnx.commit()


if __name__ == '__main__':
    main()
