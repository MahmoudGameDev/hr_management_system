// c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\mobile_app\src\features\leave\LeaveListScreen.js
import React, { useState, useEffect, useContext, useCallback } from 'react';
import { View, Text, FlatList, StyleSheet, ActivityIndicator, TouchableOpacity, RefreshControl, Alert } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { AuthContext } from '../../navigation/AuthProvider';
import { getLeaveRequests as apiGetLeaveRequests, cancelLeaveRequest } from '../../api/apiService';
import { getCachedLeaveRequests, cacheLeaveRequests, openDatabase } from '../../services/database';

const LeaveListScreen = ({ navigation }) => {
  const { userToken } = useContext(AuthContext);
  const [leaveRequests, setLeaveRequests] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [cancellingId, setCancellingId] = useState(null); // To show loader on specific item

  const loadAndFetchRequests = async (isInitialLoad = false) => {
    if (!userToken) return;

    // Only show full-screen loader on initial load if no cached data exists
    if (isInitialLoad && leaveRequests.length === 0) {
      setIsLoading(true);
    }
    setError(null);

    try {
      // Attempt to fetch fresh data from API
      const apiData = await apiGetLeaveRequests(); // Add params if your API supports pagination/filtering
      const freshRequests = apiData.requests || apiData || [];
      setLeaveRequests(freshRequests);
      await cacheLeaveRequests(freshRequests); // Cache the fresh data
    } catch (err) {
      console.error("Failed to fetch fresh leave requests from API:", err);
      // If API fails, we rely on cached data (already loaded or loaded below)
      // If there's no cached data either (e.g. first launch offline), then show an error.
      if (leaveRequests.length === 0) { // Check if we have any data (cached or otherwise)
        setError(err.message || 'Failed to load leave requests. Please check your connection.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const loadInitialData = async () => {
    await openDatabase(); // Ensure DB is open and tables are created
    setIsLoading(true); // Show loader for initial cache load attempt
    const cachedData = await getCachedLeaveRequests();
    if (cachedData && cachedData.length > 0) {
      setLeaveRequests(cachedData);
    }
    setIsLoading(false); // Hide loader after cache attempt
    await loadAndFetchRequests(true); // Then try to fetch fresh data from API, marking it as initial
  };

  // Fetch on initial mount and when screen comes into focus
  useFocusEffect(
    useCallback(() => {
      loadInitialData(); // Load cached then fetch from API
    }, [userToken]) // Re-fetch if userToken changes (e.g., re-login)
  );

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await loadAndFetchRequests(); // On pull-to-refresh, try to get fresh data
    setRefreshing(false);
  }, [userToken]);
  const handleCancelRequest = async (requestId) => {
    Alert.alert(
      "Confirm Cancellation",
      "Are you sure you want to cancel this leave request?",
      [
        { text: "No", style: "cancel" },
        {
          text: "Yes, Cancel",
          onPress: async () => {
            setCancellingId(requestId);
            try {
              await cancelLeaveRequest(requestId);
              Alert.alert("Success", "Leave request cancelled.");
              loadInitialData(); // Refresh the list (load cache then API)
            } catch (err) {
              console.error("Failed to cancel leave request:", err);
              Alert.alert("Error", err.response?.data?.error || "Could not cancel leave request.");
            } finally {
              setCancellingId(null);
            }
          },
          style: "destructive",
        },
      ]
    );
  };
  
  const renderItem = ({ item }) => (
    <TouchableOpacity
      style={styles.itemContainer}
      onPress={() => navigation.navigate('LeaveDetail', { 
          leaveRequest: item,
          // Pass a callback to refresh the list if cancellation happens on detail screen
          onGoBackRefresh: loadInitialData 
      })}
      disabled={cancellingId !== null} // Disable navigation while a cancel operation is in progress
    >
      <View>
        <Text style={styles.itemText}>Type: {item.leave_type_name || item.leave_type?.name || item.leave_type_id || 'N/A'}</Text>
        <Text style={styles.itemText}>Start: {new Date(item.start_date).toLocaleDateString()}</Text>
        <Text style={styles.itemText}>End: {new Date(item.end_date).toLocaleDateString()}</Text>
        <Text style={styles.itemText}>Status: {item.status}</Text>
        {item.reason && <Text style={styles.itemText} numberOfLines={1} ellipsizeMode="tail">Reason: {item.reason}</Text>}
        {item.status && item.status.toLowerCase() === 'pending' && (
          cancellingId === item.id ? (
            <ActivityIndicator size="small" color="#FF6B6B" style={styles.cancelLoader} />
          ) : (
            <TouchableOpacity
              style={styles.cancelButton}
              onPress={() => handleCancelRequest(item.id)}
              disabled={cancellingId !== null}
            >
              <Text style={styles.cancelButtonText}>Cancel</Text>
            </TouchableOpacity>
          )
        )}
      </View>
    </TouchableOpacity>
  );

  if (isLoading && !refreshing && leaveRequests.length === 0) {
    return <View style={styles.centered}><ActivityIndicator size="large" color="#007ACC" /></View>;
  }

  if (error) {
    return <View style={styles.centered}><Text style={styles.errorText}>{error}</Text></View>;
  }

  return (
    <View style={styles.container}>
      <TouchableOpacity
        style={styles.newRequestButton}
        onPress={() => navigation.navigate('NewLeaveRequest')}
      >
        <Text style={styles.newRequestButtonText}>Apply for Leave</Text>
      </TouchableOpacity>
      {leaveRequests.length === 0 && !isLoading ? (
        <View style={styles.centered}><Text style={styles.emptyText}>No leave requests found.</Text></View>
      ) : (
        <FlatList
          data={leaveRequests}
          renderItem={renderItem}
          keyExtractor={(item) => item.id?.toString() || Math.random().toString()}
          contentContainerStyle={styles.listContentContainer}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#E0E0E0" />
          }
        />
      )}
    </View>
  );
};

// Add StyleSheet (see previous examples for night mode styling)
const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#2B2B2B', padding: 10 },
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  errorText: { color: '#FF6B6B', fontSize: 16 },
  emptyText: { color: '#E0E0E0', fontSize: 16 },
  itemContainer: { backgroundColor: '#3C3C3C', padding: 15, marginBottom: 10, borderRadius: 8 },
  itemText: { color: '#E0E0E0', fontSize: 15, marginBottom: 3 },
  listContentContainer: { paddingBottom: 20 },
  newRequestButton: { backgroundColor: '#007ACC', paddingVertical: 12, paddingHorizontal: 20, borderRadius: 8, alignItems: 'center', marginBottom: 15, marginHorizontal:10 },
  newRequestButtonText: { color: '#FFFFFF', fontSize: 16, fontWeight: 'bold' },
  cancelButton: { backgroundColor: '#FF6B6B', paddingVertical: 8, paddingHorizontal: 12, borderRadius: 6, alignItems: 'center', marginTop: 10, alignSelf: 'flex-start' },
  cancelButtonText: { color: '#FFFFFF', fontSize: 14 },
  cancelLoader: { marginTop: 10, alignSelf: 'flex-start' }
});

export default LeaveListScreen;