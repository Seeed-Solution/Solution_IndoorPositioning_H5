/**
 * 存储辅助模块
 * 封装微信小程序本地存储操作
 */

const app = getApp();

/**
 * 保存Beacon列表到本地存储
 * @param {Array} beacons Beacon数组
 * @returns {Boolean} 操作是否成功
 */
function saveBeacons(beacons) {
  try {
    wx.setStorageSync('beacons', beacons);
    app.globalData.beacons = beacons;
    console.log('Beacon列表已保存到本地存储，数量:', beacons.length);
    return true;
  } catch (e) {
    console.error('保存Beacon列表失败:', e);
    return false;
  }
}

/**
 * 从本地存储加载Beacon列表
 * @returns {Array} Beacon数组，如果失败返回空数组
 */
function loadBeacons() {
  try {
    const beacons = wx.getStorageSync('beacons');
    if (beacons && Array.isArray(beacons)) {
      console.log('从存储加载Beacon配置，数量:', beacons.length);
      app.globalData.beacons = beacons;
      return beacons;
    } else {
      console.log('未找到有效的Beacon配置');
      app.globalData.beacons = [];
      return [];
    }
  } catch (e) {
    console.error('加载Beacon配置失败:', e);
    app.globalData.beacons = [];
    return [];
  }
}

/**
 * 保存地图信息到本地存储
 * @param {Object} mapInfo 地图信息对象
 * @returns {Boolean} 操作是否成功
 */
function saveMapInfo(mapInfo) {
  try {
    wx.setStorageSync('mapInfo', mapInfo);
    app.globalData.mapInfo = mapInfo;
    console.log('地图信息已保存到本地存储');
    return true;
  } catch (e) {
    console.error('保存地图信息到本地存储失败:', e);
    return false;
  }
}

/**
 * 从本地存储加载地图信息
 * @returns {Object|null} 地图信息对象，如果失败返回null
 */
function loadMapInfo() {
  try {
    const mapInfo = wx.getStorageSync('mapInfo');
    
    if (mapInfo) {
      console.log('从存储加载地图配置');
      
      // 验证JSON地图数据
      if (mapInfo.fileType === 'json' && mapInfo.jsonContent) {
        // 确保jsonContent是对象而不是字符串
        if (typeof mapInfo.jsonContent === 'string') {
          try {
            mapInfo.jsonContent = JSON.parse(mapInfo.jsonContent);
            console.log('解析JSON地图字符串成功');
          } catch (e) {
            console.error('解析JSON地图字符串失败:', e);
            return null;
          }
        }
      }
      
      app.globalData.mapInfo = mapInfo;
      return mapInfo;
    } else {
      console.log('未找到存储的地图配置');
      app.globalData.mapInfo = null;
      return null;
    }
  } catch (e) {
    console.error('加载地图配置失败:', e);
    app.globalData.mapInfo = null;
    return null;
  }
}

/**
 * 保存信号传播因子到本地存储
 * @param {Number} factor 信号传播因子
 * @returns {Boolean} 操作是否成功
 */
function saveSignalFactor(factor) {
  try {
    if (typeof factor !== 'number' || isNaN(factor) || factor <= 0) {
      console.error('无效的信号传播因子:', factor);
      return false;
    }
    
    wx.setStorageSync('signalPathLossExponent', factor);
    app.globalData.signalPathLossExponent = factor;
    console.log('信号传播因子已保存:', factor);
    return true;
  } catch (e) {
    console.error('保存信号传播因子失败:', e);
    return false;
  }
}

/**
 * 从本地存储加载信号传播因子
 * @returns {Number} 信号传播因子，如果失败返回默认值2.5
 */
function loadSignalFactor() {
  try {
    const n = wx.getStorageSync('signalPathLossExponent');
    if (n) {
      const nValue = Number(n);
      if (!isNaN(nValue) && nValue > 0) {
        console.log('从存储加载信号传播因子:', nValue);
        app.globalData.signalPathLossExponent = nValue;
        return nValue;
      }
    }
    
    console.log('未找到有效的信号传播因子，使用默认值:2.5');
    app.globalData.signalPathLossExponent = 2.5;
    return 2.5;
  } catch (e) {
    console.error('加载信号传播因子失败:', e);
    app.globalData.signalPathLossExponent = 2.5;
    return 2.5;
  }
}

/**
 * 加载所有本地存储数据
 * @returns {Object} 加载的数据 {beacons, mapInfo, signalFactor}
 */
function loadAllStorageData() {
  const beacons = loadBeacons();
  const mapInfo = loadMapInfo();
  const signalFactor = loadSignalFactor();
  
  return {
    beacons,
    mapInfo,
    signalFactor
  };
}

module.exports = {
  saveBeacons,
  loadBeacons,
  saveMapInfo,
  loadMapInfo,
  saveSignalFactor,
  loadSignalFactor,
  loadAllStorageData
}; 