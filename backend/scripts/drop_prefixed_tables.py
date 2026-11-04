import pymysql
from sqlalchemy.engine import make_url

from app.core.config import get_settings

url = make_url(get_settings().DATABASE_URL)
con = pymysql.connect(
    host=url.host,
    port=url.port or 3306,
    user=url.username,
    password=url.password,
    database="candidate_screening",
    autocommit=True,
)
cur = con.cursor()
cur.execute("SHOW TABLES")
names = [row[0] for row in cur.fetchall()]
cur.execute("SET FOREIGN_KEY_CHECKS=0")
for name in names:
    cur.execute(f"DROP TABLE IF EXISTS `{name}`")
cur.execute("SET FOREIGN_KEY_CHECKS=1")
print("dropped", len(names))
cur.execute("SHOW DATABASES")
print([row[0] for row in cur.fetchall() if str(row[0]).startswith("candidate_screening")])
