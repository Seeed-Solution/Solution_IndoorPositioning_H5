# -*- coding: utf-8 -*-
from datetime import datetime
from typing import List, Tuple
from sqlalchemy import Column, String, CHAR, DateTime, JSON, Integer, and_
from server.dao.base_dao import BaseDao, Base
from server.models import DeviceAlarmRecord


class DeviceAlarmRecordTable(Base):
    __tablename__ = 'device_alarm_record_list'

    id = Column(Integer, primary_key=True, autoincrement=True)
    dev_eui = Column(CHAR(16), primary_key=False, nullable=False, comment='设备 EUI')
    alarm_time = Column(DateTime, nullable=False, comment='报警时间')
    create_time = Column(DateTime, nullable=False, comment='创建时间')
    pos_type = Column(String(20), nullable=False, default='bluetooth', comment='定位类型 gps/bluetooth')
    loc = Column(JSON, nullable=False, comment='定位坐标对象 {"x": 111, "y": 222}')
    beacons = Column(JSON, nullable=True, comment='附近信标数组')
    sos = Column(Integer, nullable=False, comment='SOS状态: 0恢复, 1触发, 2未知')
    map_name = Column(String(255), nullable=True, default='unknown', comment='发生告警时所在的地图名称')


class DeviceAlarmRecordDao(BaseDao[DeviceAlarmRecord]):
    
    def __init__(self):
        super().__init__(DeviceAlarmRecordTable, DeviceAlarmRecord)
    
    def create_record(self, dev_eui: str, loc: dict, pos_type: str = 'gps', alarm_time: datetime = None,
                      beacons: List = None, sos: int = 2, map_name: str = None) -> DeviceAlarmRecord:
        """创建设备报警记录"""
        if not alarm_time:
            alarm_time = datetime.now()
        return self.create(
            dev_eui=dev_eui,
            alarm_time=alarm_time,
            create_time=datetime.now(),
            pos_type=pos_type,
            loc=loc,
            beacons=beacons,
            sos=sos,
            map_name=map_name
        )
    
    def get_records_by_dev_eui(self, dev_eui: str, page: int = 1, 
                              page_size: int = 20, map_name: str = None) -> Tuple[List[DeviceAlarmRecord], int]:
        """根据设备EUI和地图名称分页查询报警记录"""
        filters = {"dev_eui": dev_eui}
        if map_name:
            filters["map_name"] = map_name
            
        return self.find_by_filters(
            page=page,
            page_size=page_size,
            order_by='id',
            desc_order=True,
            **filters
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