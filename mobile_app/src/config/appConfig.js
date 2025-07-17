// c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\mobile_app\src\config\appConfig.js

const ENV = {
  development: {
    API_BASE_URL: 'http://10.0.2.2:5001/api', // Android emulator
    // API_BASE_URL: 'http://localhost:5001/api', // iOS simulator
  },
  production: {
    API_BASE_URL: 'https://your-deployed-api.com/api', // Replace with your actual production URL
  },
};

// You can switch environments here or use an environment variable
export const APP_CONFIG = ENV.development;