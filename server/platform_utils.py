# server/platform_utils.py
"""
平台兼容性工具函数 - 服务端版本
处理不同操作系统下的设备ID和MAC地址映射
"""

import platform
from typing import List, Dict, Any, Optional
import logging

log = logging.getLogger(__name__)

def detect_operating_system() -> str:
    """
    检测当前服务器操作系统
    @returns: 'linux' | 'windows' | 'darwin' | 'unknown'
    """
    system = platform.system().lower()
    if 'linux' in system:
        return 'linux'
    elif 'windows' in system:
        return 'windows'
    elif 'darwin' in system:
        return 'darwin'  # macOS
    else:
        return 'unknown'

def is_mac_address_supported() -> bool:
    """
    检查当前平台是否支持MAC地址获取
    @returns: True if MAC address can be obtained (Linux/Windows), False for macOS
    """
    os_type = detect_operating_system()
    return os_type in ['linux', 'windows']

def normalize_mac_address(mac: str) -> str:
    """
    统一 MAC 地址格式为大写带冒号格式 (XX:XX:XX:XX:XX:XX)
    """
    if not mac:
        return mac
    
    # 移除所有非字母数字字符
    clean_mac = ''.join(c for c in mac if c.isalnum()).upper()
    
    # 确保是12位十六进制字符
    if len(clean_mac) == 12:
        # 转换为 XX:XX:XX:XX:XX:XX 格式
        return ':'.join(clean_mac[i:i+2] for i in range(0, 12, 2))
    
    # 如果已经是正确格式，直接返回大写版本
    return mac.upper()

def process_beacon_for_platform(beacon: Dict[str, Any], os_type: Optional[str] = None) -> Dict[str, Any]:
    """
    根据操作系统处理beacon的MAC地址映射
    @param beacon: beacon数据字典
    @param os_type: 操作系统类型，如果为None则自动检测
    @returns: 处理后的beacon数据
    """
    if os_type is None:
        os_type = detect_operating_system()
    
    processed_beacon = beacon.copy()
    
    # 统一处理：直接将 deviceId 映射为 macAddress，然后删除 deviceId
    if 'deviceId' in processed_beacon and processed_beacon['deviceId']:
        # 如果 macAddress 为空或未设置，则使用 deviceId 的值
        if 'macAddress' not in processed_beacon or not processed_beacon['macAddress'] or processed_beacon['macAddress'].strip() == '':
            processed_beacon['macAddress'] = processed_beacon['deviceId']
            log.debug(f"[Platform Utils] {os_type} detected: mapped deviceId '{processed_beacon['deviceId']}' to macAddress")
        
        # 删除 deviceId 字段，统一使用 macAddress
        del processed_beacon['deviceId']
        log.debug(f"[Platform Utils] Removed deviceId field, using macAddress: '{processed_beacon['macAddress']}'")
    
    # 统一 MAC 地址格式
    if 'macAddress' in processed_beacon and processed_beacon['macAddress']:
        original_mac = processed_beacon['macAddress']
        processed_beacon['macAddress'] = normalize_mac_address(original_mac)
        if original_mac != processed_beacon['macAddress']:
            log.debug(f"[Platform Utils] Normalized MAC address: '{original_mac}' -> '{processed_beacon['macAddress']}'")
    
    # 移除个别 beacon 的 is_darwin 字段（如果存在）
    if 'is_darwin' in processed_beacon:
        del processed_beacon['is_darwin']
        log.debug("[Platform Utils] Removed is_darwin field from individual beacon")
    
    return processed_beacon

def process_beacons_for_platform(beacons: List[Dict[str, Any]], os_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    批量处理beacon列表的平台兼容性
    @param beacons: beacon数据列表
    @param os_type: 操作系统类型，如果为None则自动检测
    @returns: 处理后的beacon数据列表
    """
    if not isinstance(beacons, list):
        return beacons
    
    if os_type is None:
        os_type = detect_operating_system()
    
    log.debug(f"[Platform Utils] Processing {len(beacons)} beacons for platform: {os_type}")
    
    return [process_beacon_for_platform(beacon, os_type) for beacon in beacons]

def process_config_for_platform(config_dict: Dict[str, Any], os_type: Optional[str] = None) -> Dict[str, Any]:
    """
    处理整个配置文件的平台兼容性
    @param config_dict: 配置字典
    @param os_type: 操作系统类型，如果为None则自动检测
    @returns: 处理后的配置字典
    """
    if os_type is None:
        os_type = detect_operating_system()
    
    processed_config = config_dict.copy()
    
    # 处理 beacons 列表
    if 'beacons' in processed_config and isinstance(processed_config['beacons'], list):
        processed_config['beacons'] = process_beacons_for_platform(processed_config['beacons'], os_type)
    
    # 设置全局 is_darwin 标识
    processed_config['is_darwin'] = (os_type == 'darwin')
    log.debug(f"[Platform Utils] Set global is_darwin={processed_config['is_darwin']} for server platform: {os_type}")
    
    return processed_config

def get_platform_info() -> Dict[str, str]:
    """
    获取平台信息
    @returns: 包含平台信息的字典
    """
    return {
        'system': platform.system(),
        'release': platform.release(),
        'version': platform.version(),
        'machine': platform.machine(),
        'processor': platform.processor(),
        'detected_os': detect_operating_system(),
        'mac_address_supported': is_mac_address_supported()
    }