import ssl
from email.utils import formatdate

from django.core.management.commands import runserver
from django.core.servers import basehttp
from django.core.servers.basehttp import ServerHandler, WSGIRequestHandler, WSGIServer

from pathlib import Path

CERTIFICATE_DIR = Path(__file__).resolve().parents[3] / ".certs"
CERTIFICATE_PATH = CERTIFICATE_DIR / "localhost.pem"
PRIVATE_KEY_PATH = CERTIFICATE_DIR / "localhost-key.pem"


class SecureServerHandler(ServerHandler):
    server_software = "Kofre"


class SecureWSGIRequestHandler(WSGIRequestHandler):
    server_version = "Kofre"
    sys_version = ""

    def send_response(self, code, message=None):
        self.log_request(code)
        self.send_response_only(code, message)
        self.send_header("Date", formatdate(usegmt=True))


class SecureWSGIServer(WSGIServer):
    certificate_path = None
    private_key_path = None
    RequestHandlerClass = SecureWSGIRequestHandler

    def finish_request(self, request, client_address):
        self.RequestHandlerClass(request, client_address, self)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(
            certfile=self.certificate_path,
            keyfile=self.private_key_path,
        )
        self.socket = context.wrap_socket(self.socket, server_side=True)

    def setup_environ(self):
        super().setup_environ()
        # The socket is TLS, so tell WSGI the scheme is https. Without this Django
        # builds http:// absolute URLs (OIDC discovery) and fails CSRF origin checks.
        self.base_environ["HTTPS"] = "on"


class Command(runserver.Command):
    help = "Run the local Django server over HTTPS with a trusted localhost certificate."
    protocol = "https"
    server_cls = SecureWSGIServer

    def handle(self, *args, **options):
        SecureWSGIServer.certificate_path = str(CERTIFICATE_PATH)
        SecureWSGIServer.private_key_path = str(PRIVATE_KEY_PATH)
        basehttp.WSGIRequestHandler = SecureWSGIRequestHandler
        basehttp.ServerHandler = SecureServerHandler
        options["addrport"] = options["addrport"] or "127.0.0.1:8080"
        super().handle(*args, **options)
