/**
 * Dashboard Configuration Service
 * 专门处理 /api/configuration/dashboard 接口的前端服务层
 */
import { loadDashboardConfiguration } from './configApiService.js'

/**
 * 获取仪表板配置数据
 * @returns {Promise<DashboardConfig>} 仪表板配置对象
 */
export async function getDashboardConfig() {
  try {
    const dashboardConfig = await loadDashboardConfiguration()
    
    // 数据格式验证和标准化
    if (!dashboardConfig || !Array.isArray(dashboardConfig.maps)) {
      console.warn('Dashboard config is empty or invalid, returning default structure')
      return {
        maps: []
      }
    }
    
    // 确保每个 map 配置都有完整的结构
    const normalizedMaps = dashboardConfig.maps.map(mapConfig => ({
      map: mapConfig.map || null,
      beacons: Array.isArray(mapConfig.beacons) ? mapConfig.beacons : [],
      settings: mapConfig.settings || { signalPropagationFactor: 2.5 },
      is_darwin: mapConfig.is_darwin || false
    }))
    
    return {
      maps: normalizedMaps
    }
  } catch (error) {
    console.error('Error fetching dashboard configuration:', error)
    throw error
  }
}

/**
 * 获取所有地图列表
 * @returns {Promise<Array>} 地图配置数组
 */
export async function getAllMaps() {
  const dashboardConfig = await getDashboardConfig()
  return dashboardConfig.maps || []
}

/**
 * 根据地图名称获取特定地图配置
 * @param {string} mapName - 地图名称
 * @returns {Promise<SingleMapConfig|null>} 地图配置对象
 */
export async function getMapByName(mapName) {
  const maps = await getAllMaps()
  return maps.find(mapConfig => mapConfig.map?.name === mapName) || null
}

/**
 * 获取所有信标数据（来自所有地图）
 * @returns {Promise<Array>} 信标配置数组
 */
export async function getAllBeacons() {
  const maps = await getAllMaps()
  const allBeacons = []
  
  maps.forEach(mapConfig => {
    if (Array.isArray(mapConfig.beacons)) {
      // 为每个信标添加地图信息
      const beaconsWithMap = mapConfig.beacons.map(beacon => ({
        ...beacon,
        mapName: mapConfig.map?.name || 'Unknown Map'
      }))
      allBeacons.push(...beaconsWithMap)
    }
  })
  
  return allBeacons
}

/**
 * 按地图分组获取信标数据
 * @returns {Promise<Object>} 按地图名称分组的信标对象
 */
export async function getBeaconsByMap() {
  const maps = await getAllMaps()
  const beaconsByMap = {}
  
  maps.forEach(mapConfig => {
    const mapName = mapConfig.map?.name || 'Unknown Map'
    beaconsByMap[mapName] = mapConfig.beacons || []
  })
  
  return beaconsByMap
}

/**
 * 获取地图总数统计
 * @returns {Promise<Object>} 统计信息对象
 */
export async function getDashboardStats() {
  const maps = await getAllMaps()
  const allBeacons = await getAllBeacons()
  
  return {
    totalMaps: maps.length,
    totalBeacons: allBeacons.length,
    mapsWithBeacons: maps.filter(m => m.beacons && m.beacons.length > 0).length,
    averageBeaconsPerMap: maps.length > 0 ? Math.round(allBeacons.length / maps.length * 100) / 100 : 0
  }
}