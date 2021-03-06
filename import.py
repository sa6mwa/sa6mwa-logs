#!/usr/bin/env python
# Import/update one or more ADIF logs into a single log.
# DE SA6MWA https://github.com/sa6mwa/sa6mwa-logs
# based on ADIF.PY by OK4BX http://web.bxhome.org
import sys, getopt, os
import re
import datetime
import time
import glob
ADIF_REC_RE = re.compile(r'<(.*?):(\d+).*?>([^<\t\f\v]+)')

def parse(fn):
  raw = re.split('<eor>|<eoh>(?i)', open(fn).read() )
  logbook =[]
  for record in raw[1:-1]:
    qso = {}
    tags = ADIF_REC_RE.findall(record)
    for tag in tags:
      qso[tag[0].lower()] = tag[2][:int(tag[1])]
    logbook.append(qso)    
  return logbook

def sortlogbook(data):
  for i in range(len(data)):
    # convert all entries into lower case and ensure qso_date and time_on exists
    data[i] = {k.lower(): v for k, v in data[i].items()}
    if 'qso_date' not in data[i]:
      data[i]['qso_date'] = ""
    if 'time_on' not in data[i]:
      data[i]['time_on'] = ""
  return sorted(data, key = lambda x: x['qso_date'] + x['time_on'])

def save(operator, fn, data):
  fh=open(fn,'w')
  fh.write('Log: %s\nGenerated by SA6MWA import.py\nhttps://github.com/sa6mwa/sa6mwa-logs\nbased on ADIF.PY by OK4BX\nhttp://web.bxhome.org\n<EOH>\n' % fn)
  for qso in sortlogbook(data):
    if "operator" not in qso and operator:
      qso["operator"] = operator.upper()
    for key in sorted(qso):
      value = qso[key]
      fh.write('<%s:%i>%s ' % (key.upper(), len(value), value))
    fh.write('<EOR>\n')
  fh.close()

def conv_datetime(adi_date, adi_time):
  return datetime.datetime.strptime(adi_date+adi_time.ljust(6,"0"), "%Y%m%d%H%M%S")

def compareQSO(qso1, qso2):
  match_keys = [ "call", "mode", "band" ]
  qso1 = { k.lower(): v for k, v in qso1.items() }
  qso2 = { k.lower(): v for k, v in qso2.items() }
  match = True
  for qso in [ qso1, qso2 ]:
    assert "qso_date" in qso, "qso_date not in qso: {}".format(qso)
    assert "time_on" in qso, "time_on not in qso: {}".format(qso)
  for k in match_keys:
    for qso in [ qso1, qso2 ]:
      assert k in qso, "required key {} is not in qso: {}".format(k, qso)
    qso1time = conv_datetime(qso1["qso_date"], qso1["time_on"])
    qso2time = conv_datetime(qso2["qso_date"], qso2["time_on"])
    if qso1time != qso2time:
      match = False
    if qso1[k] != qso2[k]:
      match = False
  return match

def qso_not_in_logbook(qso, logbook, hours=0):
  # returns True if qso is not in logbook or if hours > 0, return False (as if
  # qso was in logbook) if qso is older than hours old
  retval = True
  if hours > 0:
    for k in [ "qso_date", "time_on" ]:
      assert k in qso, "required key {} is not in qso: {}".format(k, qso)
    after = datetime.datetime.utcnow() - datetime.timedelta(hours=hours)
    qsotime = conv_datetime(qso["qso_date"], qso["time_on"])
    if qsotime < after:
      return False
  for lbqso in logbook:
    if compareQSO(qso, lbqso):
      retval = False
  return retval

def usage():
  print """usage:
{} -a destinationlog.adif [-c operator] [-l hours] [-n] sourcelog1.adif [sourcelog2.adif...]
  -a, --logfile destinationlog  Log file to append QSOs to
  -c, --operator operator       Add or replace operator field with this value
  -l, --last hours              Only import QSOs dated within the last x hours
  -n, --dry-run                 Only show what would be imported, do not
                                modify destination log
""".format(sys.argv[0]),
def main():
  try:
    opts, adifs = getopt.getopt(sys.argv[1:], "ha:c:nl:", ["help","logfile=","operator=","dry-run","last="])
  except getopt.GetoptError as err:
    print str(err)
    usage()
    sys.exit(2)
  destinationlog = None
  operator = None
  dryrun = False
  hours = 0.0
  for o, a in opts:
    if o in ("-h", "--help"):
      usage()
      sys.exit()
    elif o in ("-a", "--logfile"):
      destinationlog = a
    elif o in ("-c", "--operator"):
      operator = a.upper()
    elif o in ("-n", "--dry-run"):
      dryrun = True
    elif o in ("-l", "--last"):
      hours = float(a)
    else:
      assert False, "unhandled option"
  if not destinationlog or len(adifs) < 1:
    usage()
    sys.exit(2)
  logbook = list()
  if os.path.exists(destinationlog):
    if not os.path.isfile(destinationlog):
      print "error: %s is not a file!" % destinationlog
      sys.exit(1)
    logbook = parse(destinationlog)
  logbook_original_length = len(logbook)
  for f in adifs:
    flogbook = parse(f)
    for qso in flogbook:
      if qso_not_in_logbook(qso, logbook, hours):
        prefix = "Adding"
        if dryrun:
          prefix = "Will add"
        print "{}: {}, {}, {}, {}, {}".format(prefix, qso["call"], qso["qso_date"], qso["time_on"], qso["mode"], qso["band"])
        logbook.append(qso)
  if len(logbook) > 0 and len(logbook) > logbook_original_length:
    if not dryrun:
      save(operator, destinationlog, logbook)
      print "Saved " + destinationlog
  else:
    print "Nothing to add to %s." % destinationlog
if __name__ == '__main__':
  main()
