from TogglPy.TogglPy import Toggl
from redmine import Redmine
import datetime
import math
import logging
import yaml  # PyYAML

logging.basicConfig(level=logging.WARN)

# read config file
with open("config.yml", 'r') as ymlfile:
    cfg = yaml.load(ymlfile)
    logging.debug(cfg)
# get inverted activity list
inv_activity = {v: k for k, v in cfg['redmine']['activity'].items()}


# redmine interface
redmine = Redmine(url=cfg['redmine']['url'],
                  key=cfg['redmine']['token']
                  )
# get current redmine user by token
redmine_user = redmine.user.get('current')

# Map activity types
activity = cfg['redmine']['activity']

# toggl interface
toggl = Toggl()
toggl.setAPIKey(cfg['toggl']['api_token'])
# get workspace id
workspace_id = toggl.getWorkspaces()[0]['id']
# dates range
dt = datetime.date.today() - datetime.timedelta(days=cfg['days'])
date_start = dt
date_end = datetime.date.today()
logging.info('start date: '+str(date_start))
logging.info('end date: '+str(date_end))


# get report from toggle
data = {
    'workspace_id': workspace_id,
    'since': date_start,
    'until': date_end
}


def roundtime(time):
    """
    Convert toggle time entries to redmine and round it up to .25 h
    :param time: integer from toggle
    :return: float of time entry in hours rounded up to .25
    """
    return math.ceil(time / 900000) / 4.


def get_activity(time_entry):
    """
    separate issue id and activity for redmine
    The line should start with '#issue'
    :param time_entry: string from toggle time_entry
    :return: dict of 'issue' int , 'activity' string
    """
    return {'issue': time_entry.split(' ', 1)[0][1:],
            'comments': time_entry.split(' ', 1)[1]
            }


# put data into redmine
def put2redmine(entry):
    """
    put
    :param entry: list of activity entry
    :return: None
    """
    redmine.time_entry.create(issue_id=entry['issue'],
                              spent_on=date_start,
                              hours=entry['time'],
                              activity_id=activity[entry['project']],
                              comments=entry['comments']
                              )


def get_toggle_raw_report_data(day):
    """
    get raw report data from toggle
    :return: list of entries from toggle group by project
    """
    data = {
        'workspace_id': workspace_id,
        'since': day,
        'until': day
    }
    raw_report = toggl.getSummaryReport(data)
    raw_report_data = raw_report['data']

    return raw_report_data


# run sync for all days in the range
while date_start <= date_end:
    report = []
    logging.info('-'*20)
    logging.info(date_start)
    for items in get_toggle_raw_report_data(date_start):
        for item in items['items']:
            try:
                entry = {
                    'project': items['title']['project'],
                    'client': items['title']['client'],
                    'time': roundtime(item['time'])
                }
                entry.update(get_activity(item['title']['time_entry']))
                report.append(entry)
            except IndexError:  # usually because time entry without #number TODO: add check client and validation
                pass

    # HERE PUT to redmine
    # get current redmine entries for the date
    r = list(redmine.time_entry.filter(spent_on=date_start,
                                       user_id=int(redmine_user)))
    redmine_entries = [{'issue': str(e.issue),
                        'time': float(e.hours),
                        'comments': str(e.comments),
                        'client': cfg['toggl']['client'],
                        'project': inv_activity[int(e.activity)]
                        } for e in r]
    print(date_start)
    logging.debug('Current redmine entries:')
    logging.debug(redmine_entries)

    for entry in report:
        if entry not in redmine_entries:
            logging.info(entry)

            try:
                put2redmine(entry)
                logging.info('new entry: '+str(entry))
                print(entry)
            except:
                pass
        else:
            print('entry already in: ' + str(entry))

    # go to next day
    date_start += datetime.timedelta(days=1)


