from configparser import RawConfigParser

class Task(object):

    def __init__(self, date, session):
        self.date = date
        self.session = session
        self.finished = False

class TaskList(object):

    def __init__(self, task_list):
        self._data = task_list

    def query_session(self, date, sess):
        for task in self._data:
            if task.date == date and task.session == sess:
                return task
        return None

    def remove_finished(self):
        self._data = [task for task in self._data if not task.finished]

    def __bool__(self):
        return len(self._data) > 0


class Parser(object):

    _DEFAULT_CONFIG_PATH = './config.ini'

    def __init__(self, path=_DEFAULT_CONFIG_PATH):
        self._parser = RawConfigParser()
        self._parser.read(path)

    def parse_tasks(self):
        tasks = []
        for sect in self._parser.sections():
            if not sect.startswith('task'):
                continue
            date = self._parser.getint(sect, "date")
            sess = self._parser.getint(sect, "session")
            tasks.append(Task(date, sess))
        return tasks
    
    def parse_config(self, tag="client"):
        keys = self._parser.options(tag)
        config = dict()
        for k in keys:
            raw = self._parser.get(tag, k)
            try:
                raw = float(raw)
            except:
                pass
            finally:
                config[k] = raw
        