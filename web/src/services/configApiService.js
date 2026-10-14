import httpClient from '../utils/httpClient.js';
import { API_ENDPOINTS } from '../config/api.js';

export const loadWebConfiguration = async () => {
  try {
    const response = await httpClient.get(API_ENDPOINTS.CONFIG_WEB);
    return response.data; // FastAPI should return the WebUIConfig model or null/default
  } catch (error) {
    console.error('Error loading web configuration from server:', error);
    // Enhance error handling: check error.response for server-side error details
    if (error.response) {
      throw new Error(`Server error (${error.response.status}): ${error.response.data.detail || error.message}`);
    } else if (error.request) {
      throw new Error('Network error: Could not connect to server to load configuration.');
    } else {
      throw new Error(`Failed to load web configuration: ${error.message}`);
    }
  }
};

export const loadDashboardConfiguration = async () => {
  try {
    const response = await httpClient.get(API_ENDPOINTS.CONFIG_DASHBOARD);
    return response.data; // FastAPI should return the DashboardConfig model or null/default
  } catch (error) {
    console.error('Error loading dashboard configuration from server:', error);
    // Enhance error handling: check error.response for server-side error details
    if (error.response) {
      throw new Error(`Server error (${error.response.status}): ${error.response.data.detail || error.message}`);
    } else if (error.request) {
      throw new Error('Network error: Could not connect to server to load configuration.');
    } else {
      throw new Error(`Failed to load dashboard configuration: ${error.message}`);
    }
  }
};

export const saveDashboardConfiguration = async (dashboardConfig) => {
  try {
    const response = await httpClient.post(API_ENDPOINTS.CONFIG_DASHBOARD, dashboardConfig);
    return response.data; // Should return a success message, e.g., {"message": "..."}
  } catch (error) {
    console.error('Error saving dashboard configuration to server:', error);
    if (error.response) {
      throw new Error(`Server error (${error.response.status}): ${error.response.data.detail || error.message}`);
    } else if (error.request) {
      throw new Error('Network error: Could not connect to server to save configuration.');
    } else {
      throw new Error(`Failed to save dashboard configuration: ${error.message}`);
    }
  }
};

export const saveWebConfiguration = async (configData) => {
  try {
    const response = await httpClient.post(API_ENDPOINTS.CONFIG_WEB, configData);
    return response.data; // Should return a success message, e.g., {"message": "..."}
  } catch (error) {
    console.error('Error saving web configuration to server:', error);
    if (error.response) {
      throw new Error(`Server error (${error.response.status}): ${error.response.data.detail || error.message}`);
    } else if (error.request) {
      throw new Error('Network error: Could not connect to server to save configuration.');
    } else {
      throw new Error(`Failed to save web configuration: ${error.message}`);
    }
  }
};

// --- Methods for general server configuration (server_config.json) ---
export const loadServerConfiguration = async () => {
  try {
    const response = await httpClient.get(API_ENDPOINTS.SERVER_RUNTIME_CONFIG);
    return response.data; 
  } catch (error) {
    console.error('Error loading server runtime configuration:', error);
    if (error.response) {
      throw new Error(`Server error (${error.response.status}): ${error.response.data.detail || error.message}`);
    } else if (error.request) {
      throw new Error('Network error: Could not connect to server to load runtime configuration.');
    } else {
      throw new Error(`Failed to load server runtime configuration: ${error.message}`);
    }
  }
};

export const saveServerConfiguration = async (configData) => {
  try {
    const response = await httpClient.post(API_ENDPOINTS.SERVER_RUNTIME_CONFIG, configData);
    return response.data; 
  } catch (error) {
    console.error('Error saving server runtime configuration:', error);
    if (error.response) {
      throw new Error(`Server error (${error.response.status}): ${error.response.data.detail || error.message}`);
    } else if (error.request) {
      throw new Error('Network error: Could not connect to server to save runtime configuration.');
    } else {
      throw new Error(`Failed to save server runtime configuration: ${error.message}`);
    }
  }
};

// Function to request MQTT action (enable/disable)
export const requestMqttAction = async (action) => { // action should be 'enable' or 'disable'
  const endpoint = action === 'enable' ? API_ENDPOINTS.MQTT_CONNECT : API_ENDPOINTS.MQTT_DISCONNECT;
  try {
    const response = await httpClient.post(endpoint, {});
    return response.data; // Expecting { success: true, message: "..." } or similar
  } catch (error) {
    console.error(`Error requesting MQTT action (${action}):`, error);
    if (error.response) {
      throw new Error(`Server error (${error.response.status}) while requesting MQTT ${action}: ${error.response.data.detail || error.message}`);
    } else if (error.request) {
      throw new Error(`Network error: Could not connect to server to request MQTT ${action}.`);
    } else {
      throw new Error(`Failed to request MQTT ${action}: ${error.message}`);
    }
  }
};

// Function to get all tracker devices
export const loadTrackers = async () => {
  try {
    const response = await httpClient.get(API_ENDPOINTS.TRACKERS);
    return response.data;
  } catch (error) {
    console.error('Error loading trackers:', error);
    if (error.response) {
      throw new Error(`Server error (${error.response.status}): ${error.response.data.detail || error.message}`);
    } else if (error.request) {
      throw new Error('Network error: Could not connect to server to load trackers.');
    } else {
      throw new Error(`Failed to load trackers: ${error.message}`);
    }
  }
};

// Tracker list management APIs
export const loadAllowTrackerList = async () => {
  try {
    const response = await httpClient.get(API_ENDPOINTS.ALLOW_TRACKER_LIST);
    return response.data;
  } catch (error) {
    console.error('Error loading tracker list:', error);
    if (error.response) {
      throw new Error(`Server error (${error.response.status}): ${error.response.data.detail || error.message}`);
    } else if (error.request) {
      throw new Error('Network error: Could not connect to server to load tracker list.');
    } else {
      throw new Error(`Failed to load tracker list: ${error.message}`);
    }
  }
};

export const saveAllowTrackerList = async (trackerList) => {
  try {
    const response = await httpClient.post(API_ENDPOINTS.ALLOW_TRACKER_LIST, { tracker_list: trackerList });
    return response.data;
  } catch (error) {
    console.error('Error saving tracker list:', error);
    if (error.response) {
      throw new Error(`Server error (${error.response.status}): ${error.response.data.detail || error.message}`);
    } else if (error.request) {
      throw new Error('Network error: Could not connect to server to save tracker list.');
    } else {
      throw new Error(`Failed to save tracker list: ${error.message}`);
    }
  }
};

export const loadPaasDevices = async () => {
  try {
    const response = await httpClient.get(API_ENDPOINTS.PAAS_DEVICES);
    return response.data;
  } catch (error) {
    console.error('Error loading PaaS devices:', error);
    if (error.response) {
      throw new Error(`Server error (${error.response.status}): ${error.response.data.detail || error.message}`);
    } else if (error.request) {
      throw new Error('Network error: Could not connect to server to load PaaS devices.');
    } else {
      throw new Error(`Failed to load PaaS devices: ${error.message}`);
    }
  }
};

// 专用密码修改API
export const changePassword = async (currentPassword, newPassword) => {
  try {
    const response = await httpClient.post(API_ENDPOINTS.CHANGE_PASSWORD, {
      current_password: currentPassword,
      new_password: newPassword
    });
    return response.data;
  } catch (error) {
    console.error('Error changing password:', error);
    if (error.response) {
      // 根据不同状态码处理不同类型的错误
      const status = error.response.status;
      const detail = error.response.data.detail || error.message;
      
      if (status === 401) {
        throw new Error('Current password is incorrect');
      } else if (status === 400) {
        throw new Error(detail);
      } else {
        throw new Error(`Server error (${status}): ${detail}`);
      }
    } else if (error.request) {
      throw new Error('Network error: Could not connect to server to change password.');
    } else {
      throw new Error(`Failed to change password: ${error.message}`);
    }
  }
};

// 专门用于TrackerModeConfig组件的tracker数据获取
export const loadLatestTrackerData = async () => {
  try {
    const response = await httpClient.get(API_ENDPOINTS.TRACKERS);
    return response.data; // 返回对象格式: { "trackerId": { ...trackerData } }
  } catch (error) {
    console.error('Error loading latest tracker data:', error);
    if (error.response) {
      throw new Error(`Server error (${error.response.status}): ${error.response.data.detail || error.message}`);
    } else if (error.request) {
      throw new Error('Network error: Could not connect to server to load latest tracker data.');
    } else {
      throw new Error(`Failed to load latest tracker data: ${error.message}`);
    }
  }
};

// 更新设备信息API
export const updateDevice = async (trackerId, deviceData) => {
  try {
    const response = await httpClient.put(`/devices/${trackerId}`, deviceData);
    return response.data;
  } catch (error) {
    console.error('Error updating device:', error);
    if (error.response) {
      throw new Error(`Server error (${error.response.status}): ${error.response.data.detail || error.message}`);
    } else if (error.request) {
      throw new Error('Network error: Could not connect to server to update device.');
    } else {
      throw new Error(`Failed to update device: ${error.message}`);
    }
  }
};

// 获取设备告警历史
export const loadAlarmHistory = async (deviceEui, page = 1, pageSize = 20) => {
  try {
    const params = new URLSearchParams({
      device_eui: deviceEui,
      page: page.toString(),
      page_size: pageSize.toString()
    });
    
    const response = await httpClient.get(`${API_ENDPOINTS.LIST_ALARM}?${params}`);
    return response.data;
  } catch (error) {
    console.error('Error loading alarm history:', error);
    if (error.response) {
      throw new Error(`Server error (${error.response.status}): ${error.response.data.detail || error.message}`);
    } else if (error.request) {
      throw new Error('Network error: Could not connect to server to load alarm history.');
    } else {
      throw new Error(`Failed to load alarm history: ${error.message}`);
    }
  }
};

// You might add other API calls related to configuration here later. 
/**
 * 写回一张平面图与室外地图的配准参数。
 * 只动 dashboard_config.json 里这一张地图的 registration，不覆盖整份配置。
 */
export const saveMapRegistration = async (mapName, registration) => {
  try {
    const url = `${API_ENDPOINTS.CONFIG_DASHBOARD}/maps/${encodeURIComponent(mapName)}/registration`;
    const response = await httpClient.put(url, registration);
    return response.data;
  } catch (error) {
    console.error('Error saving map registration to server:', error);
    if (error.response) {
      const detail = error.response.data?.detail;
      throw new Error(`Server error (${error.response.status}): ${
        typeof detail === 'string' ? detail : JSON.stringify(detail || error.message)}`);
    } else if (error.request) {
      throw new Error('Network error: Could not connect to server to save map registration.');
    }
    throw new Error(`Failed to save map registration: ${error.message}`);
  }
};

/** 读一张平面图的配准参数；未配准返回 null。 */
export const loadMapRegistration = async (mapName) => {
  try {
    const url = `${API_ENDPOINTS.CONFIG_DASHBOARD}/maps/${encodeURIComponent(mapName)}/registration`;
    const response = await httpClient.get(url);
    return response.data ?? null;
  } catch (error) {
    console.error('Error loading map registration from server:', error);
    return null;
  }
};
