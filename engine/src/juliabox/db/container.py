import json
import datetime
import pytz

from boto.dynamodb2.fields import HashKey
from boto.dynamodb2.types import STRING

from juliabox.db import JBoxDB, JBoxDBItemNotFound
from juliabox.jbox_util import unique_sessname

class JBoxSessionProps(JBoxDB):
    NAME = 'jbox_session'

    SCHEMA = [
        HashKey('session_id', data_type=STRING)
    ]

    INDEXES = None
    GLOBAL_INDEXES = None

    TABLE = None

    KEYS = ['session_id']
    ATTRIBUTES = ['user_id', 'snapshot_id', 'message', 'instance_id', 'attach_time', 'container_state', 'login_state', 'loading_percent']
    SQL_INDEXES = None
    KEYS_TYPES = [JBoxDB.VCHAR]
    TYPES = [JBoxDB.VCHAR, JBoxDB.VCHAR, JBoxDB.VCHAR, JBoxDB.VCHAR, JBoxDB.INT, JBoxDB.VCHAR, JBoxDB.INT, JBoxDB.FLOAT]

    # maintenance runs are once in 5 minutes
    # TODO: make configurable
    SESS_UPDATE_INTERVAL = (5 * 1.5) * 60

    # Login states
    NA = 0
    DOWNLOADING = 1
    EXTRACTING = 2

    def __init__(self, cluster, session_id, create=False, user_id=None):
        if session_id.startswith("/"):
            session_id = session_id[1:]
        qsession_id = JBoxDB.qual(cluster, session_id)
        try:
            self.item = self.fetch(session_id=qsession_id)
            self.is_new = False
        except JBoxDBItemNotFound:
            if create:
                data = {
                    'session_id': qsession_id
                }
                if user_id is not None:
                    data['user_id'] = user_id
                self.create(data)
                self.item = self.fetch(session_id=qsession_id)
                self.is_new = True
            else:
                raise

    def get_user_id(self):
        return self.get_attrib('user_id')

    def set_user_id(self, user_id):
        self.set_attrib('user_id', user_id)

    def get_snapshot_id(self):
        return self.get_attrib('snapshot_id')

    def set_snapshot_id(self, snapshot_id):
        self.set_attrib('snapshot_id', snapshot_id)

    def get_instance_id(self):
        now = datetime.datetime.now(pytz.utc)
        attach_time = JBoxSessionProps.epoch_secs_to_datetime(int(self.get_attrib('attach_time', 0)))
        if (now - attach_time).total_seconds() > JBoxSessionProps.SESS_UPDATE_INTERVAL:
            return None
        return self.get_attrib('instance_id')

    def set_instance_id(self, instance_id):
        self.set_attrib('instance_id', instance_id)
        attach_time = datetime.datetime.now(pytz.utc)
        self.set_attrib('attach_time', JBoxSessionProps.datetime_to_epoch_secs(attach_time))

    def unset_instance_id(self, instance_id):
        if self.get_instance_id() == instance_id:
            self.set_instance_id("")

    def set_container_state(self, container_state):
        self.set_attrib('container_state', container_state)

    def get_container_state(self):
        self.get_attrib('container_state', '')

    @staticmethod
    def attach_instance(cluster, session_id, instance_id, container_state=None):
        sessprops = JBoxSessionProps(cluster, session_id, create=True)
        sessprops.set_instance_id(instance_id)
        if container_state:
            sessprops.set_container_state(container_state)
        sessprops.save()

    @staticmethod
    def detach_instance(cluster, session_id, instance_id):
        sessprops = JBoxSessionProps(cluster, session_id, create=True)
        sessprops.unset_instance_id(instance_id)
        sessprops.set_container_state('')
        sessprops.save()

    def get_message(self):
        msg = self.get_attrib('message')
        if msg is not None:
            msg = json.loads(msg)
        return msg

    def set_message(self, message, delete_on_display=True):
        msg = {
            'msg': message,
            'del': delete_on_display
        }
        self.set_attrib('message', json.dumps(msg))

    @staticmethod
    def get_active_sessions(cluster):
        now = datetime.datetime.now(pytz.utc)
        nowsecs = JBoxSessionProps.datetime_to_epoch_secs(now)
        valid_time = nowsecs - JBoxSessionProps.SESS_UPDATE_INTERVAL
        result = dict()
        for record in JBoxSessionProps.scan(session_id__beginswith=cluster, attach_time__gte=valid_time,
                                            instance_id__gt=" "):
            instance_id = record.get('instance_id', None)
            if instance_id:
                sessions = result.get(instance_id, dict())
                sessions[record.get('session_id')] = record.get('container_state', 'Unknown')
                result[instance_id] = sessions
        return result

    @staticmethod
    def _get_sessp(cluster, sessname=None, email=None):
        if not sessname:
            sessname = unique_sessname(email)
        return JBoxSessionProps(cluster, sessname)

    @staticmethod
    def set_login_state(cluster, state, sessname=None, email=None):
        sessp = JBoxSessionProps._get_sessp(cluster, sessname, email)
        sessp.set_attrib('login_state', state)
        sessp.save()

    @staticmethod
    def set_login_percent(cluster, percent, sessname=None, email=None):
        sessp = JBoxSessionProps._get_sessp(cluster, sessname, email)
        sessp.set_attrib('login_percent', percent)
        sessp.save()

    @staticmethod
    def unset_login_data(cluster, sessname=None, email=None):
        JBoxSessionProps.set_login_state(cluster, JBoxSessionProps.NA, 0.0,
                                         sessname, email)

    @staticmethod
    def get_login_data(cluster, sessname=None, email=None):
        sessp = JBoxSessionProps._get_sessp(cluster, sessname, email)
        return sessp.get_attrib('login_state'), sessp.get_attrib('login_percent')
