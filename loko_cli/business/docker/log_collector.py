import uuid


class LogCollector:
    def __init__(self, observers=None):
        self.logs = {}
        self.statuses = {}
        self.observers = observers or []

    def add_log(self, k):
        self.logs[k] = []

    def remove_log(self, k):
        if k in self.logs:
            del self.logs[k]

    def get_logs(self, k):
        return self.logs.get(k, [])

    async def __call__(self, value):
        if value.get("Type") == "container":
            status = f"Container event: {value['status']}"
            name = value['Actor']['Attributes']['name']
            if name in self.logs:
                self.logs[name].append(
                    dict(type="log", channel="DEBUG", name=name, msg=status, log_id=str(uuid.uuid4())))
                if len(self.logs[name]) > 250:
                    self.logs[name] = self.logs[name][-200:]
                self.statuses[name] = status
                if self.observers:
                    for o in self.observers:
                        await o(dict(type="logs", name=name))
                        await o(dict(type="events", name=name))

        if value.get("type") == "log":
            name = value.get("name")
            if name in self.logs:
                self.logs[name].append(
                    dict(type="log", channel=value.get('channel', 'DEBUG'), msg=value.get('msg'),
                         log_id=str(uuid.uuid4())))
                if self.observers:
                    for o in self.observers:
                        await o(dict(type="logs", name=name))
