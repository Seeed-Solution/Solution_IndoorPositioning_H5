
from sqlalchemy import create_engine, func
from sqlalchemy import (
    Column,
    String,
    Integer,
    BigInteger,
    SmallInteger,
    DECIMAL,
    Text,
    DateTime,
    CHAR,
    Index,
)

from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

Base = declarative_base()

class DeviceEntity(Base):
    __tablename__ = "device_entity_list"

    dev_eui = Column(CHAR(16), primary_key=True, nullable=False, comment='设备 EUI')
    dev_name = Column(String(64), nullable=False, comment='设备名称')
    add_time = Column(DateTime, nullable=False, comment='添加时间')
    delete_time = Column(DateTime, nullable=True, comment='删除时间')