// c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\mobile_app\src\features\dashboard\DashboardScreen.js
import React, { useContext, useState, useCallback } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ActivityIndicator, ScrollView } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { AuthContext } from '../../navigation/AuthProvider'; // Adjust path as needed
import { getLeaveBalance } from '../../api/apiService'; // Assuming you have this

const DashboardScreen = ({ navigation }) => { // Assuming navigation prop is passed
  const { logout, userData } = useContext(AuthContext);
  const [leaveBalance, setLeaveBalance] = useState(null);
  const [isLoadingBalance, setIsLoadingBalance] = useState(false);
  const [balanceError, setBalanceError] = useState(null);

  const fetchLeaveBalance = useCallback(async () => {
    setIsLoadingBalance(true);
    setBalanceError(null);
    try {
      const balanceData = await getLeaveBalance();
      setLeaveBalance(balanceData);
    } catch (error) {
      console.error("Failed to fetch leave balance:", error);
      setBalanceError("Could not load leave balance.");
    } finally {
      setIsLoadingBalance(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      fetchLeaveBalance();
    }, [fetchLeaveBalance])
  );

  return (
    <ScrollView contentContainerStyle={styles.scrollContainer} style={styles.outerContainer}>
      <Text style={styles.title}>Welcome to the HR Dashboard!</Text>
      {userData && (
        <Text style={styles.userInfo}>
          Logged in as: {userData.employee_id || userData.name || 'User'}
        </Text>
      )}
      <Text style={styles.placeholderText}>
        Quick actions and summaries:
      </Text>

      <View style={styles.balanceContainer}>
        <Text style={styles.balanceTitle}>Leave Balances</Text>
        {isLoadingBalance ? (
          <ActivityIndicator color="#007ACC" />
        ) : balanceError ? (
          <Text style={styles.errorText}>{balanceError}</Text>
        ) : leaveBalance ? (
          <>
            <Text style={styles.balanceText}>Annual Leave: {leaveBalance.annual_leave_balance ?? 'N/A'}</Text>
            <Text style={styles.balanceText}>Sick Leave: {leaveBalance.sick_leave_balance ?? 'N/A'}</Text>
            {/* Add other leave types as needed */}
          </>
        ) : <Text style={styles.balanceText}>No balance data available.</Text>}
      </View>

      <TouchableOpacity
        style={[styles.button, styles.profileButton]}
        onPress={() => navigation.navigate('Profile')} // Assuming you'll have a Profile screen
      >
        <Text style={styles.buttonText}>Go to Profile (Placeholder)</Text>
      </TouchableOpacity>
      <TouchableOpacity
        style={[styles.button, styles.leaveButton]}
        onPress={() => navigation.navigate('LeaveRequests')}
      >
        <Text style={styles.buttonText}>My Leave Requests</Text>
      </TouchableOpacity>
      <TouchableOpacity
        style={[styles.button, styles.logoutButton]}
        onPress={() => logout()}
      >
        <Text style={styles.buttonText}>Logout</Text>
      </TouchableOpacity>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  outerContainer: {
    flex: 1,
    backgroundColor: '#2B2B2B', // Night mode background
  },
  scrollContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#E0E0E0', // Night mode font
    marginBottom: 20,
  },
  userInfo: {
    fontSize: 16,
    color: '#B0B0B0', // Lighter gray for secondary text
    marginBottom: 20,
  },
  placeholderText: {
    fontSize: 16,
    color: '#E0E0E0',
    textAlign: 'center',
    marginBottom: 30,
  },
  balanceContainer: {
    width: '90%',
    backgroundColor: '#3C3C3C',
    padding: 15,
    borderRadius: 8,
    marginBottom: 20,
    alignItems: 'center',
  },
  balanceTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#E0E0E0',
    marginBottom: 10,
  },
  balanceText: {
    fontSize: 16,
    color: '#E0E0E0',
    marginBottom: 5,
  },
  errorText: {
    color: '#FF6B6B',
    fontSize: 15,
  },
  button: {
    paddingVertical: 12,
    paddingHorizontal: 30,
    borderRadius: 8,
    alignItems: 'center',
    marginBottom: 15,
    width: '80%',
  },
  profileButton: {
    backgroundColor: '#007ACC', // Distinctive blue
  },
  leaveButton: {
    backgroundColor: '#4CAF50', // A green color for leave
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

export default DashboardScreen;