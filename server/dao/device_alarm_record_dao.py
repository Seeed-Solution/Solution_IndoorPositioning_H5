# -*- coding: utf-8 -*-
from datetime import datetime
from typing import List, Tuple
from sqlalchemy import Column, String, CHAR, DateTime, JSON, Integer, and_
from sqlalchemy.orm import declarative_base
from server.dao.base_dao import BaseDao
from server.models import DeviceAlarmRecord

# SQLAlchemy 表定义
Base = declarative_base()

class DeviceAlarmRecordTable(Base):
    __tablename__ = 'device_alarm_record_list'

    id = Column(Integer, primary_key=True, autoincrement=True)
    dev_eui = Column(CHAR(16), primary_key=False, nullable=False, comment='设备 EUI')
    alarm_time = Column(DateTime, nullable=False, comment='报警时间')
    create_time = Column(DateTime, nullable=False, comment='创建时间')
    pos_type = Column(String(20), nullable=False, default='bluetooth', comment='定位类型 gps/bluetooth')
    loc = Column(JSON, nullable=False, comment='定位坐标对象 {"x": 111, "y": 222}')
    beacons = Column(JSON, nullable=True, comment='附近信标数组')


class DeviceAlarmRecordDao(BaseDao[DeviceAlarmRecord]):
    
    def __init__(self):
        super().__init__(DeviceAlarmRecordTable, DeviceAlarmRecord)
    
    def create_record(self, dev_eui: str, loc: dict, pos_type: str = 'gps', alarm_time: datetime = None,
                      beacons: List = None) -> DeviceAlarmRecord:
        """创建设备报警记录"""
        if not alarm_time:
            alarm_time = datetime.now()
        return self.create(
            dev_eui=dev_eui,
            alarm_time=alarm_time,
            create_time=datetime.now(),
            pos_type=pos_type,
            loc=loc,
            beacons=beacons
        )
    
    def get_records_by_dev_eui(self, dev_eui: str, page: int = 1, 
                              page_size: int = 20) -> Tuple[List[DeviceAlarmRecord], int]:
        """根据设备EUI分页查询报警记录"""
        return self.find_by_filters(
            page=page,
            page_size=page_size,
            order_by='alarm_time',
            desc_order=True,
            dev_eui=dev_eui
        )
    
    def clear_device_records(self, dev_eui: str) -> int:
        """清空设备所有报警记录"""
        with self.get_session() as session:
            return session.query(self.table_class).filter(
                self.table_class.dev_eui == dev_eui
            ).delete()
    
    def delete_records_by_time_range(self, dev_eui: str, start_time: datetime, 
                                   end_time: datetime) -> int:
        """根据时间范围删除设备报警记录"""
        with self.get_session() as session:
            return session.query(self.table_class).filter(
                and_(
                    self.table_class.dev_eui == dev_eui,
                    self.table_class.alarm_time >= start_time,
                    self.table_class.alarm_time <= end_time
                )
            ).delete()


alarm_record_dao = DeviceAlarmRecordDao()