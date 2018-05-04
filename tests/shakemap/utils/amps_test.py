#!/usr/bin/env python

import os.path
from datetime import datetime
import shutil
import time

import numpy as np

from shakemap.utils.config import get_config_paths
from shakemap.utils.amps import AmplitudeHandler, timestr_to_timestamp
import shakemap.utils.queue as queue


def test_amps():
    try:
        install_path, data_path = get_config_paths()

        # dbfile location
        homedir = os.path.dirname(os.path.abspath(__file__))
        dbfile = os.path.join(homedir, '..', '..', 'data', 'install', 'data',
                              'amps.db')

        if os.path.isfile(dbfile):
            os.remove(dbfile)
        handler = AmplitudeHandler(install_path, data_path)

        # test inserting events into the database
        event = {'id': 'ci37889959',
                 'netid': 'ci',
                 'network': '',
                 'time': datetime(2018, 3, 7, 18, 5, 0).strftime(
                    queue.TIMEFMT),
                 'lat': 35.487,
                 'lon': -120.027,
                 'depth': 8.0,
                 'locstring': 'Somewhere in California',
                 'mag': 3.7}
        handler.insertEvent(event)
        info = handler.getStats()
        assert info['events'] == 1

        # Try getting and updating an event
        event_out = handler.getEvent('ci37889959')
        current_time = time.time()
        del event_out['network']
        event_out['repeats'] = [1, 2, 3]
        event_out['lastrun'] = current_time
        handler.insertEvent(event_out, update=True)

        event_out = handler.getEvent('ci37889959')
        assert event_out['network'] == ''
        assert set(event_out['repeats']) == set([1, 2, 3])
        assert event_out['lastrun'] == current_time

        homedir = os.path.dirname(os.path.abspath(__file__))
        xmlfile = os.path.join(homedir, '..', '..', 'data', 'ampdata',
                               'USR_100416_20180307_180450.xml')

        handler.insertAmps(xmlfile)
        info = handler.getStats()
        assert info['events'] == 1
        assert info['stations'] == 1
        assert info['station_min'] == datetime(2018, 3, 7, 18, 4, 49)
        assert info['station_max'] == datetime(2018, 3, 7, 18, 4, 49)
        assert info['channels'] == 3
        assert info['pgms'] == 15
        eqtime = timestr_to_timestamp(event['time'])
        eqlat = event['lat']
        eqlon = event['lon']
        df = handler.associate(eqtime, eqlat, eqlon)
        vsum = 0
        for row in df:
            if row[2] == 'pga':
                vsum += row[3]
        np.testing.assert_almost_equal(vsum, 0.010621814475025483)

        # get repeats
        repeats = handler.getRepeats()
        assert repeats[0][0] == 'ci37889959'
        assert set(repeats[0][2]) == set([1, 2, 3])
        # delete event
        handler.deleteEvent('ci37889959')
        info = handler.getStats()
        assert info['events'] == 0
        assert handler.getEvent('ci37889959') is None

        del handler
        os.remove(dbfile)

        # test global associator
        handler = AmplitudeHandler(install_path, data_path)
        handler.insertEvent(event)
        handler.insertAmps(xmlfile)
        associated = handler.associateAll(pretty_print=True)
        assert len(associated) == 1

        del handler
        os.remove(dbfile)
        shutil.rmtree(os.path.join(data_path, event['id']))

        # test event associator
        handler = AmplitudeHandler(install_path, data_path)
        handler.insertEvent(event)
        handler.insertAmps(xmlfile)
        associated = handler.associateOne(event['id'], pretty_print=False)
        assert associated == 15

        del handler
        os.remove(dbfile)
        shutil.rmtree(os.path.join(data_path, event['id']))

        # test clean methods
        handler = AmplitudeHandler(install_path, data_path)
        handler.insertEvent(event)
        handler.insertAmps(xmlfile)
        # Add another event with the alternate time encoding
        xmlfile = os.path.join(homedir, '..', '..', 'data', 'ampdata',
                               'TA109C_BH..2018_095_193003x.xml')
        handler.insertAmps(xmlfile)
        info = handler.getStats()
        assert info['stations'] == 2
        handler.cleanEvents(threshold=1)
        handler.cleanAmps(threshold=1)
        info = handler.getStats()
        assert info['events'] == 0
        assert info['stations'] == 0
        assert info['channels'] == 0
        assert info['pgms'] == 0
    except Exception:
        assert 1 == 2
    finally:
        if os.path.isfile(dbfile):
            os.remove(dbfile)


if __name__ == '__main__':
    os.environ['CALLED_FROM_PYTEST'] = 'True'
    test_amps()
