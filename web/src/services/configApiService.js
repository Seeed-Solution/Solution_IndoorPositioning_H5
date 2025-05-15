import axios from 'axios';

const API_BASE_URL = '/api'; // Assuming your FastAPI backend is served on the same domain

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const loadWebConfiguration = async () => {
  try {
    const response = await apiClient.get('/configuration/web');
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

export const saveWebConfiguration = async (configData) => {
  try {
    const response = await apiClient.post('/configuration/web', configData);
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
    const response = await apiClient.get('/server-runtime-config'); // Changed endpoint
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
    const response = await apiClient.post('/server-runtime-config', configData); // Changed endpoint
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
  const endpoint = action === 'enable' ? '/mqtt/connect' : '/mqtt/disconnect'; // Adjusted to match common patterns like connect/disconnect
  try {
    const response = await apiClient.post(endpoint, {}); // Sending an empty JSON object as payload, adjust if backend expects specific data
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

// You might add other API calls related to configuration here later. 