// c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\mobile_app\App.js
import React from 'react';
import { StatusBar } from 'react-native';
import { AuthProvider } from './src/navigation/AuthProvider'; // Adjust path if necessary
import AppNavigator from './src/navigation/AppNavigator';   // Adjust path if necessary

const App = () => {
  return (
    <AuthProvider>
      {/* You can set the StatusBar style globally here */}
      {/* For night mode, 'light-content' is usually appropriate */}
      <StatusBar barStyle="light-content" backgroundColor="#2B2B2B" />
      <AppNavigator />
    </AuthProvider>
  );
};

export default App;