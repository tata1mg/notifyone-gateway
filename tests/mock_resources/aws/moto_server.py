from moto.server import ThreadedMotoServer


SERVER = None


class MockServers:

    _servers = dict()

    @staticmethod
    def _get_key(host, port):
        return "%s:%s", (host, port)

    @classmethod
    def setup_server(cls, host, port):
        if cls._servers.get(cls._get_key(host, port)):
            pass
        else:
            server = ThreadedMotoServer(ip_address="localhost", port=port)
            server.start()
            cls._servers[cls._get_key(host, port)] = server

        return f'http://{host}:{port}'
