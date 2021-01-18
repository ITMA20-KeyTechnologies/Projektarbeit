import os
import sys
import json
import traceback
import mysql.connector
from collections import OrderedDict
from threading import Lock

import cherrypy


class ConfigNotValidException(Exception):
    pass


class Config:
    def __init__(self, config_path):
        self.__config_path = config_path
        self.__config = OrderedDict()
        with open(self.__config_path, 'r') as config_file:
            self.__config = json.load(config_file, object_pairs_hook=OrderedDict)

    def get(self):
        return self.__config

    def set(self, new_config):
        self.__config = new_config
        with open(self.__config_path, 'w') as config_file:
            json.dump(self.__config, config_file, indent=2)






class Counting:
    def __init__(self):
        self.__config = None
        self.__fill_level = 0
        self.__lock = Lock()
        self.__capacity_maximum = None
        self.__capacity_warning_threshold = None
        self.__capacity_stop_threshold = None

    def update_config(self, config):
        self.__config = config

        capacity_maximum = self.__config.get('capacity_maximum', None)
        if capacity_maximum is None:
            raise ConfigNotValidException('capacity_maximum not found')
        self.__capacity_maximum = int(capacity_maximum)

        capacity_warning_threshold = self.__config.get('capacity_warning_threshold', None)
        if capacity_warning_threshold is None:
            raise ConfigNotValidException('capacity_warning_threshold not found')
        self.__capacity_warning_threshold = int(capacity_warning_threshold)

        capacity_stop_threshold = self.__config.get('capacity_stop_threshold', None)
        if capacity_stop_threshold is None:
            raise ConfigNotValidException('capacity_stop_threshold not found')
        self.__capacity_stop_threshold = int(capacity_stop_threshold)

    def get_fill_level(self):
        return self.__fill_level

    def get_capacity(self):
        data = {}

        capacity = self.__capacity_maximum - self.get_fill_level()
        if capacity < 0:
            capacity = 0
        data['capacity'] = capacity

        data['visualisation'] = 'ok'
        if capacity <= self.__capacity_warning_threshold:
            data['visualisation'] = 'warning'
        if capacity <= self.__capacity_stop_threshold:
            data['visualisation'] = 'stop'

        return data


    def process_datapush(self, datapush):
        increment_fill_level = self.__config.get('increment_fill_level', [])
        decrement_fill_level = self.__config.get('decrement_fill_level', [])
        if not increment_fill_level:
            raise ConfigNotValidException('increment_fill_level is not set')
        if not decrement_fill_level:
            raise ConfigNotValidException('decrement_fill_level is not set')

        for entry in datapush:
            object_type = entry.get('objectType', None)
            if object_type == 'PERSON':
                type = entry.get('type', None)
                direction = entry.get('direction', None)
                count_item = entry.get('countItem', None)
                count_item_name = None
                if count_item:
                    count_item_name = count_item.get('name', None)

                for inc in increment_fill_level:
                    if inc['type'] == type and inc['direction'] == direction and inc['name'] == count_item_name:
                        self.increment()

                for dec in decrement_fill_level:
                    if dec['type'] == type and dec['direction'] == direction and dec['name'] == count_item_name:
                        self.decrement()

    def increment(self, value=1):
        self.__lock.acquire()
        self.__fill_level += value
        self.__lock.release()

    def decrement(self, value=1):
        self.__lock.acquire()
        self.__fill_level -= value
        self.__lock.release()

    def set_to(self, value):
        self.__lock.acquire()
        self.__fill_level = value
        self.__lock.release()





class Webserver:

    def __init__(self, config, counting):
        self.__config = config
        self.__counting = counting

    @cherrypy.expose
    def index(self):
        with open(os.path.join('www', 'index.html'), 'r') as file:
            content = file.read()
            return content

    @cherrypy.expose
    def config(self):
        with open(os.path.join('www', 'index_config.html'), 'r') as file:
            content = file.read()
            return content

    @cherrypy.expose
    def monitor(self):
        with open(os.path.join('www', 'index_monitor.html'), 'r') as file:
            content = file.read()
            return content

    @cherrypy.expose
    def current_config(self):
        method = cherrypy.request.method
        if method == 'GET':
            current_config = self.__config.get()
            cherrypy.response.headers['Cache-Control'] = 'no-cache, no-store'
            cherrypy.response.headers['Pragma'] = 'no-cache'
            cherrypy.response.headers['Content-Type'] = 'application/json'
            return json.dumps(current_config).encode('utf-8')
        elif method == 'POST':
            answer = {'state': 'ok'}
            try:
                data = cherrypy.request.body.read().decode('utf-8')
                parsed_data = json.loads(data, object_pairs_hook=OrderedDict)
                self.__config.set(parsed_data)
                self.__counting.update_config(parsed_data)
            except Exception:
                answer['state'] = 'error'
                answer['message'] = traceback.format_exc()
            cherrypy.response.headers['Cache-Control'] = 'no-cache, no-store'
            cherrypy.response.headers['Pragma'] = 'no-cache'
            cherrypy.response.headers['Content-Type'] = 'application/json'
            return json.dumps(answer).encode('utf-8')

    @cherrypy.expose
    def capacity(self):
        cherrypy.response.headers['Cache-Control'] = 'no-cache, no-store'
        cherrypy.response.headers['Pragma'] = 'no-cache'
        cherrypy.response.headers['Content-Type'] = 'application/json'
        data = {}
        try:
            data = self.__counting.get_capacity()
            data['state'] = 'ok'
        except Exception:
            data['state'] = 'error'
            data['message'] = traceback.format_exc()
        return json.dumps(data).encode('utf-8')

    @cherrypy.expose
    @cherrypy.tools.allow(methods=['POST'])
    def push(self):
        try:
            data = cherrypy.request.body.read().decode('utf-8')
            if data.startswith('Data push test from Xovis sensor'):
                return
            parsed_data = json.loads(data)
            # print(json.dumps(parsed_data, indent=2))
            self.__counting.process_datapush(parsed_data)
        except Exception:
            print('An Error occurred during datapush processing:\n{}'.format(traceback.format_exc()))

    @cherrypy.expose
    @cherrypy.tools.allow(methods=['POST'])
    def cmd(self):
        answer = {'state': 'ok'}
        try:
            data = cherrypy.request.body.read().decode('utf-8')
            parsed_data = json.loads(data)
            command = parsed_data.get('cmd', None)
            if command is None:
                raise Exception('No command found')
            elif command == 'increment':
                self.__counting.increment()
            elif command == 'decrement':
                self.__counting.decrement()
            elif command == 'reset':
                self.__counting.set_to(0)
            else:
                raise Exception('Unknown command: {}'.format(command))
        except Exception:
            answer['state'] = 'error'
            answer['message'] = str(traceback.format_exc())
        cherrypy.response.headers['Cache-Control'] = 'no-cache, no-store'
        cherrypy.response.headers['Pragma'] = 'no-cache'
        cherrypy.response.headers['Content-Type'] = 'application/json'
        return json.dumps(answer).encode('utf-8')


if __name__ == '__main__':
    config = Config('config.json')

    counting = Counting()
    try:
        counting.update_config(config.get())
    except Exception:
        print('An erroc occurred during initialization:\n{}'.format(traceback.format_exc()))

    # set by Pyinstaller onefile
    # if hasattr(sys, '_MEIPASS'):
    #     os.chdir(sys._MEIPASS)

    # Cherrypy config
    conf = {
        '/': {
            'tools.sessions.on': False,
            'tools.staticdir.root': os.path.abspath(os.getcwd() + '/www')
        },
        'global': {
            'engine.autoreload.on': False,
            'server.socket_host': '[::1]',
            'server.socket_port': 3080
        },
        '/static': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': './static'
        },
        '/favicon.ico': {
            'tools.staticfile.on': False
        }
    }

    # Start webserver
    cherrypy.quickstart(Webserver(config, counting), '/', conf)
