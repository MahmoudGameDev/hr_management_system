// c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\mobile_app\src\navigation\AppNavigator.js
import React, { useContext } from 'react';
import { View, ActivityIndicator, StyleSheet } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack'; // Or createStackNavigator

import { AuthContext } from './AuthProvider';
import LoginScreen from '../features/auth/LoginScreen';
    import DashboardScreen from '../features/dashboard/DashboardScreen';
    import ProfileScreen from '../features/profile/ProfileScreen';
    import LeaveListScreen from '../features/leave/LeaveListScreen'; 
    import NewLeaveRequestScreen from '../features/leave/NewLeaveRequestScreen';
    import LeaveDetailScreen from '../features/leave/LeaveDetailScreen';
    import EditProfileScreen from '../features/profile/EditProfileScreen'; // Import EditProfileScreen

const Stack = createNativeStackNavigator(); // Or createStackNavigator()

const AuthStack = () => (
  <Stack.Navigator screenOptions={{ headerShown: false }}>
    <Stack.Screen name="Login" component={LoginScreen} />
    {/* You can add SignupScreen, ForgotPasswordScreen here */}
  </Stack.Navigator>
);

const MainAppStack = () => (
      <Stack.Navigator
        initialRouteName="Dashboard" // Set Dashboard as the first screen after login
        screenOptions={{
          headerStyle: { backgroundColor: '#3C3C3C' }, // Dark header for night mode
          headerTintColor: '#E0E0E0', // Light title color
          headerTitleStyle: { fontWeight: 'bold' },
        }}
      >
        <Stack.Screen name="Dashboard" component={DashboardScreen} options={{ title: 'HR Dashboard' }} />
        <Stack.Screen name="Profile" component={ProfileScreen} options={{ title: 'My Profile' }} />
    <Stack.Screen name="LeaveRequests" component={LeaveListScreen} options={{ title: 'My Leave Requests' }} />
    <Stack.Screen name="NewLeaveRequest" component={NewLeaveRequestScreen} options={{ title: 'New Leave Request' }} />
    <Stack.Screen name="LeaveDetail" component={LeaveDetailScreen} options={{ title: 'Leave Details' }} />
    <Stack.Screen name="EditProfile" component={EditProfileScreen} options={{ title: 'Edit Profile' }} />
  </Stack.Navigator>
);

const AppNavigator = () => {
  const { userToken, isLoading } = useContext(AuthContext);

  if (isLoading) {
    // We haven't finished checking for the token yet
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#007ACC" />
      </View>
    );
  }

  return (
    <NavigationContainer>
      {userToken ? <MainAppStack /> : <AuthStack />}
    </NavigationContainer>
  );
};

const styles = StyleSheet.create({
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
});

export default AppNavigator;