// mobile_app/src/api/apiService.js
import axios from 'axios'; // A popular library for making HTTP requests
import AsyncStorage from '@react-native-async-storage/async-storage';
import { APP_CONFIG } from '../config/appConfig'; // Import the configuration

// --- Configuration ---

const apiClient = axios.create({
  baseURL: APP_CONFIG.API_BASE_URL,
  timeout: 10000, // Request timeout in milliseconds
  headers: {
    'Content-Type': 'application/json',
    // 'X-API-KEY': 'YOUR_INITIAL_API_KEY_IF_STILL_USING_IT_FOR_TESTING' // Temporary if needed
  },
});

// --- Interceptors (Optional but Recommended for Auth) ---
// Request interceptor to add JWT token to headers
apiClient.interceptors.request.use(
  async (config) => {
    const token = await AsyncStorage.getItem('userToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    // If you're still using the X-API-KEY for some initial non-auth endpoints:
    // config.headers['X-API-KEY'] = 'YOUR_API_KEY_FROM_FLASK_APP';
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for handling global errors (e.g., 401 Unauthorized for token refresh)
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error) => {
    const originalRequest = error.config;

    // Check if it's a 401 error and not a retry request
    if (error.response && error.response.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true; // Mark it as a retry to prevent infinite loops

      try {
        const storedRefreshToken = await AsyncStorage.getItem('refreshToken');
        if (!storedRefreshToken) {
          // No refresh token, logout user or handle appropriately
          console.log('No refresh token found, logging out.');
          await logoutUser(); // Assuming logoutUser clears tokens and navigates
          // Potentially navigate to login screen from here if not handled by logoutUser
          return Promise.reject(new Error('Session expired. Please login again.'));
        }

        // Call your API to get a new access token
        const response = await apiClient.post('/refresh_token', { refreshToken: storedRefreshToken });
        const { accessToken: newAccessToken } = response.data; // Assuming your refresh endpoint returns { accessToken: '...' }

        await AsyncStorage.setItem('userToken', newAccessToken);
        apiClient.defaults.headers.common['Authorization'] = `Bearer ${newAccessToken}`;
        originalRequest.headers['Authorization'] = `Bearer ${newAccessToken}`;

        return apiClient(originalRequest); // Retry the original request with the new token
      } catch (refreshError) {
        console.error('Error refreshing token:', refreshError.response ? refreshError.response.data : refreshError.message);
        await logoutUser(); // If refresh fails, logout the user
        // Potentially navigate to login screen
        return Promise.reject(refreshError);
      }
    }
    return Promise.reject(error);
  }
);

// --- Example API Functions ---

export const getApiStatus = async () => {
  try {
    const response = await apiClient.get('/status');
    return response.data;
  } catch (error) {
    console.error('Error fetching API status:', error.response || error.message);
    throw error;
  }
};

// You will add more functions here for login, fetching profile, etc.
export const loginUser = async (credentials) => {
  try {
    const response = await apiClient.post('/login', credentials);
    // Assuming your API returns { accessToken: '...', refreshToken: '...', user: {...} }
    const { accessToken, refreshToken, user } = response.data;

    if (accessToken && refreshToken) {
      await AsyncStorage.setItem('userToken', accessToken);
      await AsyncStorage.setItem('refreshToken', refreshToken);
      apiClient.defaults.headers.common['Authorization'] = `Bearer ${accessToken}`;
    }
    // Return what's needed by the AuthProvider, e.g., token and user data
    return { token: accessToken, user }; // Or simply response.data if AuthProvider handles it
  } catch (error) {
    console.error('Error during login:', error.response ? error.response.data : error.message);
    throw error; // Re-throw to be handled by the calling component
  }
};

export const logoutUser = async () => {
  await AsyncStorage.removeItem('userToken');
  await AsyncStorage.removeItem('refreshToken');
  delete apiClient.defaults.headers.common['Authorization'];
  // Here, you might want to trigger navigation to the Login screen.
  // This is often handled by updating a global auth state (e.g., in AuthContext)
  // which then causes the AppNavigator to switch to the Auth stack.
  // For direct navigation (less ideal from here):
  // import { navigate } from '../navigation/RootNavigation'; // You'd need to set up RootNavigation
  // navigate('Login');
};

// Example: Add a function to fetch user profile
export const getUserProfile = async () => {
  try {
    const response = await apiClient.get('/profile'); // Assuming a '/profile' endpoint
    return response.data;
  } catch (error) {
    console.error('Error fetching user profile:', error.response ? error.response.data : error.message);
    throw error;
  }
};

export const updateUserProfile = async (profileData) => {
  try {
    // Using PUT, assuming you replace the entire editable part of the profile.
    // Use PATCH if you want to send only changed fields.
    const response = await apiClient.put('/profile', profileData);
    return response.data; // Expects the updated profile data or a success message
  } catch (error) {
    console.error('Error updating user profile:', error.response ? error.response.data : error.message);
    throw error;
  }
};

// --- Leave Management API Functions ---

export const getLeaveBalance = async () => {
  try {
    const response = await apiClient.get('/leave_balance'); // Adjust endpoint if needed
    return response.data; // Expects e.g., { annual_leave_balance: 10, sick_leave_balance: 5 }
  } catch (error) {
    console.error('Error fetching leave balance:', error.response ? error.response.data : error.message);
    throw error;
  }
};

export const getLeaveTypes = async () => {
  try {
    const response = await apiClient.get('/leave_types'); // Adjust endpoint if needed
    return response.data; // Expects e.g., [{ id: 1, name: 'Annual Leave' }, ...]
  } catch (error) {
    console.error('Error fetching leave types:', error.response ? error.response.data : error.message);
    throw error;
  }
};

export const getLeaveRequests = async (params) => { // params for pagination/filtering
  try {
    const response = await apiClient.get('/leave_requests', { params }); // Adjust endpoint if needed
    return response.data; // Expects e.g., { requests: [], totalPages: 1, ... }
  } catch (error) {
    console.error('Error fetching leave requests:', error.response ? error.response.data : error.message);
    throw error;
  }
};

export const submitLeaveRequest = async (leaveData) => {
  try {
    const response = await apiClient.post('/leave_requests', leaveData); // Adjust endpoint if needed
    return response.data; // Expects the created request or a success message
  } catch (error) {
    console.error('Error submitting leave request:', error.response ? error.response.data : error.message);
    throw error;
  }
};

export const cancelLeaveRequest = async (requestId) => {
  try {
    const response = await apiClient.delete(`/leave_requests/${requestId}`); // Adjust endpoint if needed
    return response.data; // Expects a success message or updated status
  } catch (error) {
    console.error(`Error cancelling leave request ${requestId}:`, error.response ? error.response.data : error.message);
    throw error;
  }
};
  
export default apiClient;