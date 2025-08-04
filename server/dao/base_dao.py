from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class BaseDao:

    def __init__(self, table_name: str):
        # 建立 SQLite 数据库连接（本地文件 app.db）
        engine = create_engine("sqlite://db/app.db", echo=True)
        session = sessionmaker(bind=engine)
        self.session = session()
        self.table_name = table_name
