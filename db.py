"""
Small PyMySQL wrapper that works like flask_mysqldb:
    mysql = MySQL(app)
    cursor = mysql.connection.cursor()
    mysql.connection.commit()
so the rest of app.py needs no changes.
"""
import os
import ssl
import pymysql
from flask import g


class MySQL:
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            app.teardown_appcontext(self._close)

    def _connect(self):
        cfg = self.app.config
        kwargs = dict(
            host=cfg["MYSQL_HOST"],
            port=int(cfg.get("MYSQL_PORT", 3306)),
            user=cfg["MYSQL_USER"],
            password=cfg["MYSQL_PASSWORD"],
            database=cfg["MYSQL_DB"],
            cursorclass=pymysql.cursors.DictCursor,   # same as MYSQL_CURSORCLASS=DictCursor before
            charset="utf8mb4",
            connect_timeout=15,
        )

        # Cloud databases (Aiven) require SSL
        ca_file = os.environ.get("DB_SSL_CA")
        if ca_file and os.path.exists(ca_file):
            kwargs["ssl"] = {"ca": ca_file}
        elif os.environ.get("DB_SSL", "").lower() in ("1", "true", "yes"):
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE   # encrypted; certificate not verified
            kwargs["ssl"] = ctx

        return pymysql.connect(**kwargs)

    @property
    def connection(self):
        if "mysql_db" not in g:
            g.mysql_db = self._connect()
        else:
            g.mysql_db.ping(reconnect=True)
        return g.mysql_db

    def _close(self, exc=None):
        conn = g.pop("mysql_db", None)
        if conn is not None:
            conn.close()
