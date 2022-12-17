import logging


class Microservice:

    def __init__(self, name, image, repository=None, ports=None, environment=None, networks=None, volumes=None, volumes_from=None,
                 expose=None, **kwargs):
        self.name = name
        self.image = image
        self.repository = repository
        self.ports = ports or []
        self.environment = environment or []
        self.networks = networks or []
        self.volumes = volumes or []
        self.expose = expose or []
        self.volumes_from = volumes_from or []
        if kwargs:
            logging.warning((self.__class__, "KWARGS", kwargs))

    # def __dict__(self):
    #     d = dict()
    #     d[self.name] = dict(image=self.image, ports=self.ports, environment=self.environment, networks=self.networks,
    #                         volumes=self.volumes)
    #     return d

    def get_body(self):
        return dict(image=self.image, ports=self.ports, environment=self.environment, networks=self.networks,
                    volumes=self.volumes)
