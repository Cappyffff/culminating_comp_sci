from zeroconf import Zeroconf, ServiceInfo
import socket


class LANDiscovery:
    def __init__(self, name="cappyffff", port=5001):
        self.name = name
        self.port = port
        self.zeroconf = Zeroconf()
        self.info = None

    def get_local_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip

    def start(self):
        ip = self.get_local_ip()

        self.info = ServiceInfo(
            "_http._tcp.local.",
            f"{self.name}._http._tcp.local.",
            addresses=[socket.inet_aton(ip)],
            port=self.port,
            properties={},
            server=f"{self.name}.local."
        )

        self.zeroconf.register_service(self.info)
        print(f"[LAN] Advertising as {self.name}.local:{self.port}")

    def stop(self):
        if self.info:
            self.zeroconf.unregister_service(self.info)
        self.zeroconf.close()