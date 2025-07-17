// c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\mobile_app\src\features\auth\LoginScreen.js
import React, { useState, useContext } from 'react';
import { View, Text, TextInput, Button, StyleSheet, Alert, ActivityIndicator, TouchableOpacity } from 'react-native';
import { AuthContext } from '../../navigation/AuthProvider'; // Import AuthContext

const LoginScreen = ({ navigation }) => { // Assuming navigation prop is passed by React Navigation
  const { login, isLoading: authContextIsLoading } = useContext(AuthContext); // Get login function and isLoading from context
  const [employeeId, setEmployeeId] = useState('');
  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false); // Local loading state for the API call
  const [error, setError] = useState('');

  const handleLogin = async () => {
    if (!employeeId.trim() || !password.trim()) {
      setError('Please enter both Employee ID and Password.');
      return;
    }
    setIsSubmitting(true);
    setError('');
    try {
      // Ensure your API expects 'employee_id' or adjust the key accordingly
      // The login function from AuthContext will internally call apiService.loginUser
      // and handle token storage and global state update.
      await login({ employee_id: employeeId, password }); // Pass credentials to context's login
      setIsSubmitting(false);
      
      // After successful login (token is stored by apiService.loginUser)
      // You need to update your app's global auth state to reflect that the user is logged in.
      // This will typically trigger a re-render in App.js to show the main app screens.
      
      // navigation.replace('MainAppStack'); // Or navigate to your main app stack
      // Navigation will happen automatically because AppNavigator listens to userToken in AuthContext

    } catch (err) {
      setIsSubmitting(false);
      const errorMessage = err.response?.data?.error || err.response?.data?.message || 'Login failed. Please check your credentials or network connection.';
      console.error('Login failed:', errorMessage);
      setError(errorMessage);
      Alert.alert('Login Failed', errorMessage);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>HR System Login</Text>
      <TextInput
        style={styles.input}
        placeholder="Employee ID"
        value={employeeId}
        onChangeText={setEmployeeId}
        autoCapitalize="none"
        keyboardType="default" // Or "email-address" if applicable
      />
      <TextInput
        style={styles.input}
        placeholder="Password"
        value={password}
        onChangeText={setPassword}
        secureTextEntry
      />
      {isSubmitting || authContextIsLoading ? ( // Show loader if either local submission or context is loading
        <ActivityIndicator size="large" color="#007ACC" style={styles.loader}/>
      ) : (
        <TouchableOpacity style={styles.button} onPress={handleLogin}>
          <Text style={styles.buttonText}>Login</Text>
        </TouchableOpacity>
      )}
      {error ? <Text style={styles.errorText}>{error}</Text> : null}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    padding: 20,
    backgroundColor: '#2B2B2B', // Night mode background
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 30,
    color: '#E0E0E0', // Night mode font
  },
  input: {
    height: 50,
    borderColor: '#4A4A4A', // Darker border for night mode
    borderWidth: 1,
    marginBottom: 15,
    paddingHorizontal: 15,
    borderRadius: 8,
    backgroundColor: '#3C3C3C', // Darker input background
    color: '#E0E0E0', // Night mode font for input text
  },
  button: {
    backgroundColor: '#007ACC', // Distinctive blue
    paddingVertical: 15,
    borderRadius: 8,
    alignItems: 'center',
    marginBottom: 10,
  },
  buttonText: {
    color: '#FFFFFF', // White text on blue button
    fontSize: 16,
    fontWeight: 'bold',
  },
  errorText: {
    color: '#FF6B6B', // A reddish error color suitable for dark mode
    textAlign: 'center',
    marginTop: 10,
  },
  loader: {
    marginVertical: 20,
  }
});

export default LoginScreen;