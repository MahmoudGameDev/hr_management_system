// c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\mobile_app\src\features\profile\EditProfileScreen.js
import React, { useState, useContext, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  StyleSheet,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { AuthContext } from '../../navigation/AuthProvider';
import { updateUserProfile } from '../../api/apiService';

const EditProfileScreen = ({ navigation }) => {
  const { userData, fetchAndSetUserData } = useContext(AuthContext); // Assuming fetchAndSetUserData will be exposed

  // Initialize state with userData or empty strings
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  // Example: Add other editable fields like contact_number
  // const [contactNumber, setContactNumber] = useState('');

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Pre-fill form when userData becomes available or changes
    if (userData) {
      setName(userData.name || '');
      setEmail(userData.email || '');
      // setContactNumber(userData.contact_number || '');
    }
  }, [userData]);

  const handleSaveChanges = async () => {
    if (!name.trim()) {
      Alert.alert("Validation Error", "Name cannot be empty.");
      return;
    }
    if (!email.trim() || !/\S+@\S+\.\S+/.test(email)) {
      Alert.alert("Validation Error", "Please enter a valid email address.");
      return;
    }
    // Add more validation as needed for other fields

    setIsSubmitting(true);
    setError(null);
    try {
      const profileDataToUpdate = {
        name,
        email,
        // contact_number: contactNumber,
        // Only include fields that your API expects for an update.
        // Some fields like employee_id or joining_date are typically not user-editable.
      };
      await updateUserProfile(profileDataToUpdate);
      setIsSubmitting(false);

      // Refresh the global user data in AuthContext
      if (fetchAndSetUserData) {
        await fetchAndSetUserData();
      }

      Alert.alert("Success", "Profile updated successfully!", [
        { text: "OK", onPress: () => navigation.goBack() }
      ]);
    } catch (err) {
      setIsSubmitting(false);
      const apiError = err.response?.data?.error || err.response?.data?.message || "Failed to update profile. Please try again.";
      console.error("Failed to update profile:", err); // Log the full error
      setError(apiError);
      Alert.alert("Update Failed", apiError);
    }
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === "ios" ? "padding" : "height"}
      style={styles.keyboardAvoidingContainer}
    >
      <ScrollView style={styles.container} contentContainerStyle={styles.contentContainer}>
        <Text style={styles.label}>Name:</Text>
        <TextInput style={styles.input} value={name} onChangeText={setName} placeholder="Full Name" placeholderTextColor="#888" />

        <Text style={styles.label}>Email:</Text>
        <TextInput style={styles.input} value={email} onChangeText={setEmail} placeholder="Email Address" keyboardType="email-address" autoCapitalize="none" placeholderTextColor="#888" />

        {/* Example for another editable field */}
        {/* <Text style={styles.label}>Contact Number:</Text>
        <TextInput style={styles.input} value={contactNumber} onChangeText={setContactNumber} placeholder="Contact Number" keyboardType="phone-pad" placeholderTextColor="#888"/> */}

        {isSubmitting ? (
          <ActivityIndicator size="large" color="#007ACC" style={styles.loader} />
        ) : (
          <TouchableOpacity style={styles.saveButton} onPress={handleSaveChanges}>
            <Text style={styles.saveButtonText}>Save Changes</Text>
          </TouchableOpacity>
        )}
        {error && <Text style={styles.errorText}>{error}</Text>}
      </ScrollView>
    </KeyboardAvoidingView>
  );
};

const styles = StyleSheet.create({
  keyboardAvoidingContainer: { flex: 1, backgroundColor: '#2B2B2B' },
  container: { flex: 1 },
  contentContainer: { padding: 20, flexGrow: 1 },
  label: { fontSize: 16, color: '#E0E0E0', marginBottom: 8, marginTop: 15 },
  input: { backgroundColor: '#3C3C3C', color: '#E0E0E0', paddingHorizontal: 15, paddingVertical: 12, borderRadius: 8, fontSize: 16, marginBottom: 15 },
  saveButton: { backgroundColor: '#007ACC', paddingVertical: 15, borderRadius: 8, alignItems: 'center', marginTop: 20 },
  saveButtonText: { color: '#FFFFFF', fontSize: 16, fontWeight: 'bold' },
  loader: { marginTop: 20 },
  errorText: { color: '#FF6B6B', textAlign: 'center', marginTop: 10, fontSize: 15 },
});

export default EditProfileScreen;