from sqlalchemy import Column, String, CHAR, DateTime, JSON
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class DeviceAlarmRecord(Base):
    __tablename__ = 'device_alarm_record_list'

    dev_eui = Column(CHAR(16), primary_key=True, nullable=False, comment='设备 EUI')
    alarm_time = Column(DateTime, nullable=False, comment='报警时间')
    create_time = Column(DateTime, nullable=False, comment='创建时间')
    pos_type = Column(String(20), nullable=False, default='blueteeth', comment='定位类型 gps/blueteeth')
    loc = Column(JSON, nullable=False, comment='定位坐标对象 {"x": 111, "y": 222}')
    beacons = Column(JSON, nullable=True, comment='附近信标数组')
