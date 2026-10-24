import ssl

from django.core.management.commands import runserver
from django.core.servers.basehttp import WSGIServer

from pathlib import Path

CERTIFICATE_DIR = Path(__file__).resolve().parents[3] / ".certs"
CERTIFICATE_PATH = CERTIFICATE_DIR / "localhost.pem"
PRIVATE_KEY_PATH = CERTIFICATE_DIR / "localhost-key.pem"


class SecureWSGIServer(WSGIServer):
    certificate_path = None
    private_key_path = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(
            certfile=self.certificate_path,
            keyfile=self.private_key_path,
        )
        self.socket = context.wrap_socket(self.socket, server_side=True)


class Command(runserver.Command):
    help = "Run the local Django server over HTTPS with a trusted localhost certificate."
    protocol = "https"
    server_cls = SecureWSGIServer

    def handle(self, *args, **options):
        SecureWSGIServer.certificate_path = str(CERTIFICATE_PATH)
        SecureWSGIServer.private_key_path = str(PRIVATE_KEY_PATH)
        options["addrport"] = options["addrport"] or "127.0.0.1:8080"
        super().handle(*args, **options)
