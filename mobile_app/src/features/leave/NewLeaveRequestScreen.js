// c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\mobile_app\src\features\leave\NewLeaveRequestScreen.js
import React, { useState, useEffect, useContext } from 'react';
import {
  View,
  Text,
  TextInput,
  StyleSheet,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
  ScrollView,
  Platform,
} from 'react-native';
import { AuthContext } from '../../navigation/AuthProvider';
import { submitLeaveRequest, getLeaveTypes } from '../../api/apiService';
import { Picker } from '@react-native-picker/picker'; // Install if not already: npm install @react-native-picker/picker
import DateTimePickerModal from "react-native-modal-datetime-picker"; // Install: npm install react-native-modal-datetime-picker

const NewLeaveRequestScreen = ({ navigation }) => {
  const { userToken } = useContext(AuthContext);
  const [leaveTypes, setLeaveTypes] = useState([]);
  const [selectedLeaveTypeId, setSelectedLeaveTypeId] = useState(null);
  const [startDate, setStartDate] = useState(null);
  const [endDate, setEndDate] = useState(null);
  const [reason, setReason] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const [isStartDatePickerVisible, setStartDatePickerVisibility] = useState(false);
  const [isEndDatePickerVisible, setEndDatePickerVisibility] = useState(false);

  useEffect(() => {
    const fetchLeaveTypes = async () => {
      try {
        const types = await getLeaveTypes();
        setLeaveTypes(types || []);
        if (types && types.length > 0) {
          setSelectedLeaveTypeId(types[0].id); // Default to first type
        }
      } catch (err) {
        console.error("Failed to fetch leave types:", err);
        Alert.alert("Error", "Could not load leave types.");
      }
    };
    fetchLeaveTypes();
  }, [userToken]);

  const handleSubmit = async () => {
    if (!selectedLeaveTypeId || !startDate || !endDate || !reason.trim()) {
      Alert.alert("Validation Error", "Please fill in all fields.");
      return;
    }
    if (new Date(endDate) < new Date(startDate)) {
      Alert.alert("Validation Error", "End date cannot be before start date.");
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      const leaveData = {
        leave_type_id: selectedLeaveTypeId,
        start_date: startDate.toISOString().split('T')[0], // Format as YYYY-MM-DD
        end_date: endDate.toISOString().split('T')[0],   // Format as YYYY-MM-DD
        reason: reason,
      };
      await submitLeaveRequest(leaveData);
      setIsSubmitting(false);
      Alert.alert("Success", "Leave request submitted successfully!", [
        { text: "OK", onPress: () => navigation.goBack() }
      ]);
    } catch (err) {
      setIsSubmitting(false);
      console.error("Failed to submit leave request:", err.response?.data || err.message);
      setError(err.response?.data?.error || err.message || "Failed to submit leave request.");
      Alert.alert("Submission Failed", error || "An unexpected error occurred.");
    }
  };

  const showDatePicker = (picker) => picker === 'start' ? setStartDatePickerVisibility(true) : setEndDatePickerVisibility(true);
  const hideDatePicker = (picker) => picker === 'start' ? setStartDatePickerVisibility(false) : setEndDatePickerVisibility(false);

  const handleConfirmDate = (date, picker) => {
    if (picker === 'start') setStartDate(date);
    else setEndDate(date);
    hideDatePicker(picker);
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.contentContainer}>
      <Text style={styles.label}>Leave Type:</Text>
      <View style={styles.pickerContainer}>
        <Picker
          selectedValue={selectedLeaveTypeId}
          onValueChange={(itemValue) => setSelectedLeaveTypeId(itemValue)}
          style={styles.picker}
          itemStyle={styles.pickerItem} // For iOS
        >
          {leaveTypes.map((type) => (
            <Picker.Item key={type.id} label={type.name} value={type.id} color={Platform.OS === 'android' ? '#E0E0E0' : undefined} />
          ))}
        </Picker>
      </View>

      <Text style={styles.label}>Start Date:</Text>
      <TouchableOpacity onPress={() => showDatePicker('start')} style={styles.dateInput}>
        <Text style={styles.dateText}>{startDate ? startDate.toLocaleDateString() : "Select Start Date"}</Text>
      </TouchableOpacity>
      <DateTimePickerModal isVisible={isStartDatePickerVisible} mode="date" onConfirm={(date) => handleConfirmDate(date, 'start')} onCancel={() => hideDatePicker('start')} />

      <Text style={styles.label}>End Date:</Text>
      <TouchableOpacity onPress={() => showDatePicker('end')} style={styles.dateInput}>
        <Text style={styles.dateText}>{endDate ? endDate.toLocaleDateString() : "Select End Date"}</Text>
      </TouchableOpacity>
      <DateTimePickerModal isVisible={isEndDatePickerVisible} mode="date" onConfirm={(date) => handleConfirmDate(date, 'end')} onCancel={() => hideDatePicker('end')} />

      <Text style={styles.label}>Reason:</Text>
      <TextInput
        style={styles.input}
        value={reason}
        onChangeText={setReason}
        placeholder="Enter reason for leave"
        placeholderTextColor="#888"
        multiline
      />

      {isSubmitting ? (
        <ActivityIndicator size="large" color="#007ACC" style={styles.loader} />
      ) : (
        <TouchableOpacity style={styles.submitButton} onPress={handleSubmit}>
          <Text style={styles.submitButtonText}>Submit Request</Text>
        </TouchableOpacity>
      )}
      {error && <Text style={styles.errorText}>{error}</Text>}
    </ScrollView>
  );
};

// Add StyleSheet (consistent with night mode)
const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#2B2B2B' },
  contentContainer: { padding: 20 },
  label: { fontSize: 16, color: '#E0E0E0', marginBottom: 8, marginTop: 15 },
  input: { backgroundColor: '#3C3C3C', color: '#E0E0E0', paddingHorizontal: 15, paddingVertical: 12, borderRadius: 8, fontSize: 16, marginBottom: 15, minHeight: 80, textAlignVertical: 'top' },
  pickerContainer: { backgroundColor: '#3C3C3C', borderRadius: 8, marginBottom: 15, borderWidth: Platform.OS === 'ios' ? 1 : 0, borderColor: Platform.OS === 'ios' ? '#4A4A4A' : undefined },
  picker: { height: Platform.OS === 'android' ? 50 : 200, color: '#E0E0E0', width: '100%' },
  pickerItem: { color: '#E0E0E0', backgroundColor: '#3C3C3C' }, // For iOS picker item text color
  dateInput: { backgroundColor: '#3C3C3C', padding: 15, borderRadius: 8, marginBottom: 15, alignItems: 'center' },
  dateText: { color: '#E0E0E0', fontSize: 16 },
  submitButton: { backgroundColor: '#007ACC', paddingVertical: 15, borderRadius: 8, alignItems: 'center', marginTop: 20 },
  submitButtonText: { color: '#FFFFFF', fontSize: 16, fontWeight: 'bold' },
  loader: { marginTop: 20 },
  errorText: { color: '#FF6B6B', textAlign: 'center', marginTop: 10, fontSize: 15 },
});

export default NewLeaveRequestScreen;