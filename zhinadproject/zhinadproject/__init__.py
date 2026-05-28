import os

# PyMySQL is easier to install on shared hosting than mysqlclient (no compiler).
if os.environ.get("DB_NAME") and "mysql" in os.environ.get("DB_ENGINE", "mysql"):
    import pymysql

    pymysql.install_as_MySQLdb()
