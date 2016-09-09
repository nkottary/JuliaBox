__author__ = "Nishanth"

import threading
import datetime
import time

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from juliabox.cloud import JBPluginCloud
from oauth2client.client import GoogleCredentials

from juliabox.jbox_util import JBoxCfg, retry_on_errors

class GoogleMonitoringV2(JBPluginCloud):
    provides = [JBPluginCloud.JBP_MONITORING,
                JBPluginCloud.JBP_MONITORING_GOOGLE,
                JBPluginCloud.JBP_MONITORING_GOOGLE_V2]
    threadlocal = threading.local()

    RFC_3339_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
    ALLOWED_CUSTOM_GCE_VALUE_TYPES = ["double", "int64"]
    ALLOWED_EC2_VALUE_TYPES = ["Percent", "Count"]
    CUSTOM_METRIC_DOMAIN = "custom.cloudmonitoring.googleapis.com/"
    SELF_STATS = dict()

    @staticmethod
    def _connect_google_monitoring():
        c = getattr(GoogleMonitoringV2.threadlocal, 'cm_conn', None)
        if c is None:
            creds = GoogleCredentials.get_application_default()
            GoogleMonitoringV2.threadlocal.cm_conn = c = build("cloudmonitoring", "v2beta2",
                                                               credentials=creds)
        return c

    @staticmethod
    def _get_google_now():
        return datetime.datetime.utcnow().strftime(GoogleMonitoringV2.RFC_3339_FORMAT)

    @staticmethod
    def _process_value_type(value_type):
        if value_type in GoogleMonitoringV2.ALLOWED_EC2_VALUE_TYPES:
            if value_type == "Count":
                return "int64"
            return "double"
        elif value_type in GoogleMonitoringV2.ALLOWED_CUSTOM_GCE_VALUE_TYPES:
            return value_type
        else:
            raise Exception("Invalid value_type argument.")

    @staticmethod
    def _get_timeseries_dict(metric_name, labels, value, value_type, timenow):
        value_type = GoogleMonitoringV2._process_value_type(value_type)
        timedesc = {
            "metric": GoogleMonitoringV2.CUSTOM_METRIC_DOMAIN + metric_name,
            "labels": labels
        }
        timeseries = {
            "timeseriesDesc": timedesc,
            "point": {
                "start": timenow,
                "end": timenow,
                value_type + "Value": value
            }
        }
        return timeseries

    @staticmethod
    @retry_on_errors(retries=2)
    def _ts_write(timeseries, install_id):
        ts = GoogleMonitoringV2._connect_google_monitoring().timeseries()
        ts.write(project=install_id,
                 body={"timeseries": timeseries}).execute()

    @staticmethod
    def _update_timeseries(timeseries):
        timenow = GoogleMonitoringV2._get_google_now()
        for ts in timeseries:
            ts['point']['start'] = timenow
            ts['point']['end'] = timenow

    @staticmethod
    def _timeseries_write(timeseries, install_id):
        try:
            GoogleMonitoringV2._ts_write(timeseries, install_id)
        except HttpError, err:
            if err.resp.status == 400:
                time.sleep(1)
                GoogleMonitoringV2._update_timeseries(timeseries)
                GoogleMonitoringV2._ts_write(timeseries, install_id)
            else:
                raise

    @staticmethod
    def publish_stats_multi(stats, instance_id, install_id, autoscale_group):
        timeseries = []
        label = {GoogleMonitoringV2.CUSTOM_METRIC_DOMAIN + 'InstanceID': instance_id,
                 GoogleMonitoringV2.CUSTOM_METRIC_DOMAIN + 'GroupID' : autoscale_group}
        timenow = GoogleMonitoringV2._get_google_now()
        for (stat_name, stat_unit, stat_value) in stats:
            GoogleMonitoringV2.SELF_STATS[stat_name] = stat_value
            GoogleMonitoringV2.log_info("CloudMonitoring %s.%s.%s=%r(%s)",
                                        install_id, instance_id, stat_name,
                                        stat_value, stat_unit)
            timeseries.append(
                GoogleMonitoringV2._get_timeseries_dict(stat_name, label,
                                                        stat_value, stat_unit,
                                                        timenow))
        GoogleMonitoringV2._timeseries_write(timeseries, install_id)

    @staticmethod
    def _list_metric(project, metric_name, labels, timespan, window, aggregator):
        ts = GoogleMonitoringV2._connect_google_monitoring().timeseries()
        nowtime = GoogleMonitoringV2._get_google_now()
        retlist = []
        nextpage = None
        labels = [GoogleMonitoringV2.CUSTOM_METRIC_DOMAIN + label for label in labels]
        while True:
            start = time.time()
            resp = None
            while True:
                try:
                    resp = ts.list(project=project, pageToken=nextpage,
                                   metric=GoogleMonitoringV2.CUSTOM_METRIC_DOMAIN + metric_name,
                                   youngest=nowtime, timespan=timespan, labels=labels,
                                   window=window, aggregator=aggregator).execute()
                    break
                except:
                    if time.time() < start + 20:
                        time.sleep(3)
                    else:
                        raise
            series = resp.get("timeseries")
            if series == None:
                break
            retlist.extend(series[0]['points'])
            nextpage = resp.get("nextPageToken")
            if nextpage == None:
                break
        return retlist

    @staticmethod
    def get_instance_stats(instance, stat_name, current_instance_id, install_id,
                           autoscale_group):
        if (instance == current_instance_id) and (stat_name in GoogleMonitoringV2.SELF_STATS):
            GoogleMonitoringV2.log_debug("Using cached self_stats. %s=%r",
                                         stat_name, GoogleMonitoringV2.SELF_STATS[stat_name])
            return GoogleMonitoringV2.SELF_STATS[stat_name]

        res = None
        labels = ['InstanceID=='+instance, 'GroupID==' + autoscale_group]
        results = GoogleMonitoringV2._list_metric(project=install_id, metric_name=stat_name,
                                                  labels=labels, timespan="30m", window="1m",
                                                  aggregator="mean")
        for _res in results:
            if (res is None) or (res['start'] < _res['start']):
                res = _res
        if res:
            valuekey = [name for name in res.keys() if name not in ["start", "end"]][0]
            return res[valuekey]
        return None

    GET_METRIC_DIMENSIONS_TIMESPAN = "30m"

    @staticmethod
    def get_metric_dimensions(metric_name, install_id, autoscale_group):
        next_token = None
        dims = {}
        tsd = GoogleMonitoringV2._connect_google_monitoring().timeseriesDescriptors()
        nowtime = GoogleMonitoringV2._get_google_now()
        labels=[GoogleMonitoringV2.CUSTOM_METRIC_DOMAIN + 'GroupID==' + autoscale_group]

        while True:
            start = time.time()
            metrics = None
            while True:
                try:
                    metrics = tsd.list(pageToken=next_token, project=install_id,
                                       metric=GoogleMonitoringV2.CUSTOM_METRIC_DOMAIN + metric_name,
                                       youngest=nowtime, labels=labels,
                                       timespan=GoogleMonitoringV2.GET_METRIC_DIMENSIONS_TIMESPAN).execute()
                    break
                except:
                    if time.time() < start + 20:
                        time.sleep(3)
                    else:
                        raise
            if metrics.get("timeseries") is None:
                break
            for m in metrics["timeseries"]:
                for n_dim, v_dim in m["labels"].iteritems():
                    key = n_dim.split('/')[-1]
                    dims[key] = dims.get(key, []) + [v_dim]
            next_token = metrics.get("nextPageToken")
            if next_token is None:
                break
        if len(dims) == 0:
            GoogleMonitoringV2.log_warn("invalid metric " + '.'.join([install_id, metric_name]))
            return None
        return dims
