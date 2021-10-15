import logging
import re
import time
import cryptography.hazmat

import singer
from snowflake.connector import DictCursor, SnowflakeConnection
from snowflake.connector.cursor import SnowflakeCursor
from snowflake.connector.json_result import DictJsonResult

# Ignore DEBUG, and INFO level messages from Snowflake Connector
logger = logging.getLogger("snowflake.connector")
logger.setLevel(logging.WARNING)


class MillisLoggingCursor(SnowflakeCursor):
    def execute(self, command, **kwargs):
        timestamp = time.monotonic()

        try:
            super(MillisLoggingCursor, self).execute(command, **kwargs)
        finally:
            self.connection.LOGGER.info(
            "MillisLoggingCursor: {} millis spent executing: {}".format(
                int((time.monotonic() - timestamp) * 1000),
                re.sub(r'\n', '  \\\\n  ', command)
            ))

        return self


class MillisLoggingDictCursor(MillisLoggingCursor):
    def __init__(self, connection):
        MillisLoggingCursor.__init__(self, connection, DictJsonResult)


class Connection(SnowflakeConnection):
    def __init__(self, **kwargs):
        self.LOGGER = singer.get_logger()

        self.configured_warehouse = kwargs.get('warehouse')
        self.configured_database = kwargs.get('database')
        self.configured_schema = kwargs.get('schema')

        if kwargs.get("private_key"):
            kwargs["private_key"] = cryptography.hazmat.primitives.serialization.load_pem_private_key(
                kwargs["private_key"].replace("\\n","\n").encode(), 
                password=kwargs["password"].encode(), 
                backend=cryptography.hazmat.backends.default_backend()
            ).private_bytes(
                encoding=cryptography.hazmat.primitives.serialization.Encoding.DER,
                format=cryptography.hazmat.primitives.serialization.PrivateFormat.PKCS8,
                encryption_algorithm=cryptography.hazmat.primitives.serialization.NoEncryption()
            )

        SnowflakeConnection.__init__(self, **kwargs)

    def cursor(self, as_dict=False):
        cursor_class = MillisLoggingCursor
        if as_dict:
            cursor_class = MillisLoggingDictCursor

        return SnowflakeConnection.cursor(self, cursor_class)

    def initialize(self, logger):
        self.LOGGER = logger


def connect(**kwargs):
    return Connection(**kwargs)
