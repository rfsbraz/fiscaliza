/**
 * API Configuration
 * Central configuration for API base URL
 */

// Use environment variable if available, otherwise use production API
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://api.fiscaliza.pt/api';


/**
 * Helper function to build API URLs
 * @param {string} endpoint - The API endpoint (without leading slash)
 * @returns {string} - Complete API URL
 */
export const buildApiUrl = (endpoint) => {
  // Remove leading slash if present
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint;
  return `${API_BASE_URL}/${cleanEndpoint}`;
};

/**
 * Helper function for API fetch calls with error handling
 * @param {string} endpoint - The API endpoint
 * @param {object} options - Fetch options
 * @returns {Promise<Response>} - Fetch response
 */
export const apiFetch = async (endpoint, options = {}) => {
  const url = buildApiUrl(endpoint);
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });
  
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${response.statusText}`);
  }
  
  return response;
};