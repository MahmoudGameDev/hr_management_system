// c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\mobile_app\src\navigation\AuthProvider.js
import React, { createContext, useState, useEffect } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { loginUser as apiLoginUser, logoutUser as apiLogoutUser, getUserProfile } from '../api/apiService';

export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [userToken, setUserToken] = useState(null);
  const [isLoading, setIsLoading] = useState(true); // To show a loading screen while checking token
  const [userData, setUserData] = useState(null); // Optional: store user details

  const fetchAndSetUserData = async () => {
    try {
      const profileData = await getUserProfile();
      if (profileData) {
        await AsyncStorage.setItem('cachedUserData', JSON.stringify(profileData));
      }
      setUserData(profileData); // Assuming getUserProfile returns the user object
    } catch (error) {
      console.error('AuthProvider: Failed to fetch user profile', error);
      // If fetching profile fails, especially due to auth (e.g., 401),
      // it implies the stored token is no longer valid.
      if (error.response && error.response.status === 401) {
        console.log('AuthProvider: Token invalid while fetching profile, logging out.');
        // Call the logout function defined later in authContext
        await authContextValue.logout(); // Use the actual context object
      }
    }
  };
  useEffect(() => {
    // Check for token on app startup
    const bootstrapAsync = async () => {
      let token;
      let cachedUser = null;
      try {
        token = await AsyncStorage.getItem('userToken');
        const cachedUserDataString = await AsyncStorage.getItem('cachedUserData');
        if (cachedUserDataString) {
          cachedUser = JSON.parse(cachedUserDataString);
          setUserData(cachedUser); // Set cached data immediately for faster UI response
        }

        if (token) {
          setUserToken(token); // Set token first so API calls can be authorized
          await fetchAndSetUserData(); // Then fetch fresh data and update cache/state
        }
      } catch (e) {
        console.error('Restoring token or cached user data failed', e);
      }
      
      setIsLoading(false);
    };
    bootstrapAsync();
  }, []);

  // Define authContextValue first so it can be referenced in fetchAndSetUserData
  const authContextValue = {
    userToken,
    userData,
    isLoading,
    fetchAndSetUserData, // Expose this function
    login: async (credentials) => {
      setIsLoading(true);
      try {
        const { token, user: loggedInUser } = await apiLoginUser(credentials); // apiService.loginUser stores tokens
        setUserToken(token);
        // Use user data from login response initially, then fetch full profile
        // which will also cache it.
        if (loggedInUser) {
          setUserData(loggedInUser); 
        }
        await fetchAndSetUserData(); // Optionally, re-fetch full profile if login response is minimal
        setIsLoading(false);
        // LoginScreen will stop its own spinner; navigation is handled by userToken change
        // No explicit return needed on success, or return true if preferred
      } catch (error) {
        console.error('AuthProvider login error:', error);
        setIsLoading(false);
        throw error; // Re-throw to be handled by LoginScreen
      }
    },
    logout: async () => {
      setIsLoading(true);
      try {
        await apiLogoutUser(); // apiService.logoutUser removes the token
        setUserToken(null);
        await AsyncStorage.removeItem('cachedUserData'); // Clear cached user data on logout
        setUserData(null);
      } catch (error) {
        console.error('AuthProvider logout error:', error);
      } finally {
        setIsLoading(false);
      }
    },
    // You can add a register function here if needed
  };

  return (
    <AuthContext.Provider value={authContextValue}>
      {children}
    </AuthContext.Provider>
  );
};