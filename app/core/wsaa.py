import base64
import os
from datetime import datetime, timedelta, timezone
from lxml import etree
import OpenSSL
from zeep import Client
from app.core.config import settings
from app.core.cache import get_wsaa_credentials, set_wsaa_credentials
import logging

logger = logging.getLogger(__name__)

class WSAA:
    SERVICE_NAME = "wgesStockDepositosFiscales"

    @staticmethod
    def generate_tra() -> str:
        """Generates the Ticket Request Authorization (TRA) XML."""
        root = etree.Element("loginTicketRequest", version="1.0")
        header = etree.SubElement(root, "header")

        # Unique ID, usually a timestamp
        unique_id = etree.SubElement(header, "uniqueId")
        unique_id.text = str(int(datetime.now().timestamp()))

        # Generation time: current time - 10 minutes (to avoid clock sync issues)
        generation_time = etree.SubElement(header, "generationTime")
        gen_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        generation_time.text = gen_time.strftime("%Y-%m-%dT%H:%M:%S-00:00")

        # Expiration time: generation time + 12 hours
        expiration_time = etree.SubElement(header, "expirationTime")
        exp_time = gen_time + timedelta(hours=12)
        expiration_time.text = exp_time.strftime("%Y-%m-%dT%H:%M:%S-00:00")

        service = etree.SubElement(root, "service")
        service.text = WSAA.SERVICE_NAME

        return etree.tostring(root, encoding="utf-8").decode("utf-8")

    @staticmethod
    def sign_tra(tra_xml: str) -> str:
        """Signs the TRA using the private key and certificate."""
        if not os.path.exists(settings.AFIP_CERT_PATH) or not os.path.exists(settings.AFIP_KEY_PATH):
            logger.error("AFIP certificate or key file not found.")
            raise Exception("Missing AFIP certificates.")

        with open(settings.AFIP_KEY_PATH, "rb") as key_file:
            key_data = key_file.read()
        with open(settings.AFIP_CERT_PATH, "rb") as cert_file:
            cert_data = cert_file.read()

        pkey = OpenSSL.crypto.load_privatekey(OpenSSL.crypto.FILETYPE_PEM, key_data)
        cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, cert_data)

        flags = OpenSSL.crypto.PKCS7_DETACHED

        # Create PKCS7 signature
        bio_in = OpenSSL.crypto.MemBio(tra_xml.encode("utf-8"))
        pkcs7 = OpenSSL.crypto.sign(cert, pkey, bio_in, b"sha256", flags)

        # Convert to DER
        bio_out = OpenSSL.crypto.MemBio()
        OpenSSL.crypto.write_pkcs7(bio_out, pkcs7)
        der_data = bio_out.read()

        # Return base64 encoded CMS
        # Note: OpenSSL.crypto.write_pkcs7 returns PEM format, we need to extract the base64 content
        # Removing the BEGIN and END lines
        pem_str = der_data.decode("utf-8")
        lines = pem_str.strip().split("\n")
        b64_signature = "".join(lines[1:-1])

        return b64_signature

    @staticmethod
    def get_credentials() -> dict:
        """Retrieves valid token and sign. Fetches new ones if expired or missing."""
        credentials = get_wsaa_credentials()
        if credentials:
            logger.info("Using cached WSAA credentials.")
            return credentials

        logger.info("Requesting new WSAA credentials.")
        try:
            tra = WSAA.generate_tra()
            cms = WSAA.sign_tra(tra)

            client = Client(settings.WSAA_WSDL_URL)
            response = client.service.loginCms(in0=cms)

            root = etree.fromstring(response.encode("utf-8"))
            token = root.find(".//token").text
            sign = root.find(".//sign").text

            set_wsaa_credentials(token, sign)
            return {"token": token, "sign": sign}
        except Exception as e:
            logger.error(f"Error obtaining WSAA credentials: {str(e)}")
            raise e
