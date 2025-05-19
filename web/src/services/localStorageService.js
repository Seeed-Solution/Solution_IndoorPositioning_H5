const LOCAL_STORAGE_KEY = 'webUIConfiguration';

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
export const loadConfigFromLocalStorage = () => {
  try {
    const serializedConfig = localStorage.getItem(LOCAL_STORAGE_KEY);
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