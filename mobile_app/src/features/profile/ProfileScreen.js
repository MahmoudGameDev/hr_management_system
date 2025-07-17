// c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\mobile_app\src\features\profile\ProfileScreen.js
import React, { useContext } from 'react';
    import { View, Text, StyleSheet, TouchableOpacity, ScrollView, ActivityIndicator, Alert } from 'react-native';
import { AuthContext } from '../../navigation/AuthProvider'; // Adjust path as needed
import { requestLocationPermission, getCurrentLocation } from '../../services/locationService'; // Import location service

const ProfileScreen = ({ navigation }) => {
  const { userData, logout, isLoading: authIsLoading } = useContext(AuthContext);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>My Profile</Text>
      {userData && (
        <View style={styles.infoContainer}>
          <Text style={styles.infoLabel}>Employee ID:</Text>
          <Text style={styles.infoValue}>{userData.employee_id ?? 'N/A'}</Text>
          <Text style={styles.infoLabel}>Name:</Text>
          <Text style={styles.infoValue}>{userData.name ?? 'N/A'}</Text>

          <Text style={styles.infoLabel}>Email:</Text>
          <Text style={styles.infoValue}>{userData.email ?? 'N/A'}</Text>

          <Text style={styles.infoLabel}>Department:</Text>
          <Text style={styles.infoValue}>{userData.department?.name ?? userData.department ?? 'N/A'}</Text>

          <Text style={styles.infoLabel}>Job Title:</Text>
          <Text style={styles.infoValue}>{userData.job_title ?? 'N/A'}</Text>

          <Text style={styles.infoLabel}>Joining Date:</Text>
          <Text style={styles.infoValue}>{userData.joining_date ? new Date(userData.joining_date).toLocaleDateString() : 'N/A'}</Text>

          {/* Add more fields like reporting manager, contact number etc. */}
          {/* e.g., <Text style={styles.infoLabel}>Email:</Text> */}
          {/* <Text style={styles.infoValue}>{userData.email || (userData.user && userData.user.email) || 'N/A'}</Text> */}
        </View>
      )}
      {authIsLoading && !userData && ( // Show loader if auth is loading and no user data yet
        <ActivityIndicator size="large" color="#007ACC" style={{ marginTop: 20 }}/>

      )}
      {/* Temporary Test Button for Location */}
      <TouchableOpacity
        style={[styles.button, {backgroundColor: 'purple', marginTop: 10}]}
        onPress={async () => {
          const hasPermission = await requestLocationPermission();
          if (hasPermission) {
            try {
              const coords = await getCurrentLocation();
              Alert.alert("Current Location", `Lat: ${coords.latitude}, Lon: ${coords.longitude}`);
            } catch (error) {
              Alert.alert("Location Error", error.message || "Could not get location.");
            }
          } else {
            Alert.alert("Permission Denied", "Location permission is required to get your position.");
          }
        }}
      >
        <Text style={styles.buttonText}>Test Get Location</Text>
      </TouchableOpacity>
      <Text style={styles.placeholderText}>
        Profile editing and more details will be available here.
      </Text>
      <TouchableOpacity
        style={[styles.button, styles.editButton]}
        onPress={() => navigation.navigate('EditProfile')}
      >
        <Text style={styles.buttonText}>Edit Profile</Text>
      </TouchableOpacity>
    <TouchableOpacity
        style={[styles.button, styles.logoutButton]}
        onPress={() => logout()}
      >
        <Text style={styles.buttonText}>Logout</Text>
      </TouchableOpacity>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    // justifyContent: 'flex-start', // Align items to top for profile view
    alignItems: 'center',
    padding: 20,
    backgroundColor: '#2B2B2B', // Night mode background
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#E0E0E0', // Night mode font
    marginBottom: 20,
    marginTop: 10,
  },
  infoContainer: {
    width: '90%',
    backgroundColor: '#3C3C3C', // Darker card background
    padding: 15,
    borderRadius: 8,
    marginBottom: 20,
  },
  infoLabel: {
    fontSize: 16,
    color: '#A0A0A0', // Lighter gray for labels
    marginBottom: 2,
  },
  infoValue: {
    fontSize: 18,
    color: '#E0E0E0',
    marginBottom: 10,
  },
  placeholderText: {
    fontSize: 16,
    color: '#E0E0E0',
    textAlign: 'center',
    marginBottom: 30,
    flex: 1, // Pushes logout button down if content is short
  },
  editButton: {
    backgroundColor: '#007ACC', 
  },
  button: {
    paddingVertical: 12,
    paddingHorizontal: 30,
    borderRadius: 8,
    alignItems: 'center',
    marginBottom: 15,
    width: '90%',
  },
  logoutButton: {
    backgroundColor: '#FF6B6B', // A reddish color for logout
  },
  buttonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: 'bold',
  },
});

export default ProfileScreen;