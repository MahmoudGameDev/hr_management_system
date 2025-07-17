// c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\mobile_app\src\features\leave\LeaveDetailScreen.js
import React, { useState, useContext } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Alert, ActivityIndicator } from 'react-native';
import { AuthContext } from '../../navigation/AuthProvider'; // Assuming AuthContext is needed for user context or token
import { cancelLeaveRequest } from '../../api/apiService'; // Import the API function

const LeaveDetailScreen = ({ route, navigation }) => {
  // Assuming the full leave request item is passed as a parameter
  const { leaveRequest: initialLeaveRequest, onGoBackRefresh } = route.params; // onGoBackRefresh is optional
  const { userToken } = useContext(AuthContext); // Needed if cancelLeaveRequest relies on global token state

  const [leaveRequest, setLeaveRequest] = useState(initialLeaveRequest);
  const [isCancelling, setIsCancelling] = useState(false);
  if (!leaveRequest) {
    return (
      <View style={styles.centered}>
        <Text style={styles.errorText}>Leave request details not found.</Text>
      </View>
    );
  }

  const handleCancelRequest = async () => {
    if (!userToken) return;
    Alert.alert(
      "Confirm Cancellation",
      "Are you sure you want to cancel this leave request?",
      [
        { text: "No", style: "cancel" },
        {
          text: "Yes, Cancel",
          onPress: async () => {
            setIsCancelling(true);
            try {
              await cancelLeaveRequest(leaveRequest.id);
              Alert.alert("Success", "Leave request cancelled successfully.");
              // Optionally, update local state or navigate back and trigger refresh
              setLeaveRequest(prev => ({ ...prev, status: 'Cancelled' })); // Optimistic update
              if (onGoBackRefresh) onGoBackRefresh(); // Call refresh callback if provided
              navigation.goBack();
            } catch (err) {
              Alert.alert("Error", err.response?.data?.error || "Could not cancel leave request.");
            } finally {
              setIsCancelling(false);
            }
          },
          style: "destructive",
        },
      ]
    );
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.contentContainer}>
      <Text style={styles.title}>Leave Request Details</Text>

      <View style={styles.detailItem}>
        <Text style={styles.label}>Leave Type:</Text>
        <Text style={styles.value}>{leaveRequest.leave_type?.name || leaveRequest.leave_type_id || 'N/A'}</Text>
      </View>

      <View style={styles.detailItem}>
        <Text style={styles.label}>Start Date:</Text>
        <Text style={styles.value}>{new Date(leaveRequest.start_date).toLocaleDateString()}</Text>
      </View>

      <View style={styles.detailItem}>
        <Text style={styles.label}>End Date:</Text>
        <Text style={styles.value}>{new Date(leaveRequest.end_date).toLocaleDateString()}</Text>
      </View>

      <View style={styles.detailItem}>
        <Text style={styles.label}>Status:</Text>
        <Text style={[styles.value, { color: getStatusColor(leaveRequest.status) }]}>{leaveRequest.status}</Text>
      </View>

      {leaveRequest.reason && (
        <View style={styles.detailItem}>
          <Text style={styles.label}>Reason:</Text>
          <Text style={styles.value}>{leaveRequest.reason}</Text>
        </View>
      )}

      {/* Add more details as needed, e.g., submission date, manager comments if applicable */}

      {leaveRequest.status && leaveRequest.status.toLowerCase() === 'pending' && (
        isCancelling ? (
          <ActivityIndicator size="large" color="#FF6B6B" style={styles.loader} />
        ) : (
          <TouchableOpacity
            style={styles.cancelButton}
            onPress={handleCancelRequest}
          >
            <Text style={styles.cancelButtonText}>Cancel Request</Text>
          </TouchableOpacity>
        )
      )}


    </ScrollView>
  );
};

const getStatusColor = (status) => {
  if (!status) return '#E0E0E0';
  const lowerStatus = status.toLowerCase();
  if (lowerStatus === 'approved') return '#4CAF50'; // Green
  if (lowerStatus === 'rejected' || lowerStatus === 'cancelled') return '#FF6B6B'; // Red
  if (lowerStatus === 'pending') return '#FFC107'; // Amber
  return '#E0E0E0'; // Default
};

// Add StyleSheet (consistent with night mode)
const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#2B2B2B' },
  contentContainer: { padding: 20 },
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#2B2B2B' },
  errorText: { color: '#FF6B6B', fontSize: 16 },
  title: { fontSize: 22, fontWeight: 'bold', color: '#E0E0E0', marginBottom: 20, textAlign: 'center' },
  detailItem: { backgroundColor: '#3C3C3C', padding: 15, borderRadius: 8, marginBottom: 12 },
  label: { fontSize: 14, color: '#A0A0A0', marginBottom: 4 },
  value: { fontSize: 17, color: '#E0E0E0' },
  cancelButton: { backgroundColor: '#FF6B6B', paddingVertical: 12, paddingHorizontal: 20, borderRadius: 8, alignItems: 'center', marginTop: 20 },
  cancelButtonText: { color: '#FFFFFF', fontSize: 16, fontWeight: 'bold' },
  loader: { marginTop: 20 },
});

export default LeaveDetailScreen;