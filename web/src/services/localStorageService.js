const LOCAL_STORAGE_KEY = 'webUIConfiguration';
const TOKEN_STORAGE_KEY = 'authToken';

/**
 * Saves the current Web UI configuration to localStorage.
 * @param {object} configData The configuration object to save.
 */
export const saveConfigToLocalStorage = (configData) => {
  try {
    const serializedConfig = JSON.stringify(configData);
    localStorage.setItem(LOCAL_STORAGE_KEY, serializedConfig);
    console.log('Configuration saved to localStorage.');
  } catch (error) {
    console.error('Error saving configuration to localStorage:', error);
    // Potentially throw the error or handle it more gracefully
    // depending on how the calling code should react.
  }
};

/**
 * Loads the Web UI configuration from localStorage.
 * @returns {object | null} The loaded configuration object, or null if not found or error.
 */
export const loadConfigFromLocalStorage = (key=null) => {
  try {
    if (!key) {
      key = LOCAL_STORAGE_KEY
    }
    const serializedConfig = localStorage.getItem(key);
    if (serializedConfig === null) {
      console.log('No configuration found in localStorage.');
      return null;
    }
    const configData = JSON.parse(serializedConfig);
    console.log('Configuration loaded from localStorage.');
    return configData;
  } catch (error) {
    console.error('Error loading configuration from localStorage:', error);
    return null;
  }
};

/**
 * Clears the Web UI configuration from localStorage.
 */
export const clearConfigFromLocalStorage = () => {
  try {
    localStorage.removeItem(LOCAL_STORAGE_KEY);
    console.log('Configuration cleared from localStorage.');
  } catch (error) {
    console.error('Error clearing configuration from localStorage:', error);
  }
};

/**
 * Saves authentication token to localStorage.
 * @param {string} token The authentication token to save.
 */
export const saveTokenToLocalStorage = (token) => {
  try {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
    console.log('Token saved to localStorage.');
  } catch (error) {
    console.error('Error saving token to localStorage:', error);
  }
};

/**
 * Loads authentication token from localStorage.
 * @returns {string | null} The token, or null if not found or error.
 */
export const getTokenFromLocalStorage = () => {
  try {
    const token = localStorage.getItem(TOKEN_STORAGE_KEY);
    if (token === null) {
      console.log('No token found in localStorage.');
      return null;
    }
    return token;
  } catch (error) {
    console.error('Error loading token from localStorage:', error);
    return null;
  }
};

/**
 * Removes authentication token from localStorage.
 */
export const removeTokenFromLocalStorage = () => {
  try {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    console.log('Token removed from localStorage.');
  } catch (error) {
    console.error('Error removing token from localStorage:', error);
  }
}; 