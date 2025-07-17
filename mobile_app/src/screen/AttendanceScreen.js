import React, {useState, useEffect, useCallback} from 'react';
import {
  View,
  Text,
  Button,
  Alert,
  StyleSheet,
  Platform,
  ActivityIndicator,
  TouchableOpacity,
} from 'react-native';
import NfcService from '../services/NfcService'; // Adjust path as needed
import {
  openDatabase,
  findEmployeeByNfcTag,
  recordAttendance,
  addDummyEmployees, // For testing
} from '../services/database'; // Adjust path as needed

const AttendanceScreen = () => {
  const [nfcStatus, setNfcStatus] = useState('Initializing NFC...');
  const [isScanning, setIsScanning] = useState(false);
  const [isLoading, setIsLoading] = useState(false); // For async operations like DB lookup
  const [attendanceMode, setAttendanceMode] = useState('entry'); // 'entry' or 'exit'
  const [nfcInitialized, setNfcInitialized] = useState(false);

  useEffect(() => {
    const initialize = async () => {
      try {
        await openDatabase(); // Ensure DB is open and tables are created
        // You might want to add dummy employees for testing if the table is empty
        // await addDummyEmployees(); // Uncomment to add dummy data on app start for testing
      } catch (dbError) {
        console.error("Failed to initialize database on screen mount:", dbError);
        Alert.alert("Database Error", "Could not initialize the local database.");
      }

      if (Platform.OS === 'android') {
        try {
          const success = await NfcService.init();
          if (success) {
            setNfcStatus('NFC Ready. Select mode and tap "Start Scanning".');
            setNfcInitialized(true);
          } else {
            setNfcStatus('NFC not supported on this device.');
            setNfcInitialized(false);
          }
        } catch (error) {
          setNfcStatus(error.message || 'Failed to initialize NFC.');
          setNfcInitialized(false);
          Alert.alert('NFC Error', error.message || 'Could not initialize NFC. Please ensure it is enabled.');
        }
      } else {
        setNfcStatus('NFC scanning is primarily for Android devices.');
        setNfcInitialized(false);
      }
    };

    initialize();

    return () => {
      if (Platform.OS === 'android' && nfcInitialized) {
        NfcService.cleanup();
      }
    };
  }, [nfcInitialized]); // Rerun if nfcInitialized changes (e.g. for cleanup)

  const handleTagDiscovered = useCallback(async (tagId, ndefMessage, rawTag) => {
    setIsScanning(false);
    setIsLoading(true);
    setNfcStatus(`Tag detected: ${tagId}. Processing...`);
    Alert.alert('Tag Scanned!', `Tag ID: ${tagId}\nNDEF: ${ndefMessage || 'N/A'}`);

    try {
      const employee = await findEmployeeByNfcTag(tagId); // Use actual DB function
      if (employee) {
        const now = new Date();
        const attendanceData = {
          employee_id: employee.id, // Use the employee's database ID
          type: attendanceMode,
          timestamp: now.toISOString(),
          // latitude: currentCoords?.latitude, // Optional: if you integrate location
          // longitude: currentCoords?.longitude, // Optional: if you integrate location
        };
        const result = await recordAttendance(attendanceData); // Use actual DB function

        if (result && result.id) { // Check if attendance was successfully inserted (got an ID back)
          Alert.alert('Success', `Attendance (${attendanceMode}) recorded for ${employee.name}.`);
          setNfcStatus(`Attendance for ${employee.name} recorded. Scan next.`);
        } else {
          Alert.alert('Error', 'Failed to record attendance in the database.');
          setNfcStatus('Failed to record attendance. Please try again.');
        }
      } else {
        Alert.alert('Employee Not Found', 'No employee associated with this NFC tag.');
        setNfcStatus('Unknown tag. Please register the tag or try another.');
      }
    } catch (error) {
      console.error("Error processing tag: ", error);
      Alert.alert('Processing Error', 'An error occurred while processing the tag.');
      setNfcStatus('Error processing tag. Please try again.');
    } finally {
      setIsLoading(false);
      // Optionally stop scanning completely or prepare for next scan
      // await NfcService.stopTagReading();
    }
  }, [attendanceMode]);

  const handleScanError = useCallback((errorCode, errorDetails) => {
    setIsScanning(false);
    setIsLoading(false);
    console.warn('NFC Scan Error:', errorCode, errorDetails);
    setNfcStatus(`Scan Error: ${errorCode}. Please try again.`);
    Alert.alert('NFC Scan Error', `Could not scan tag: ${errorCode}. Ensure NFC is enabled and tag is close.`);
  }, []);

  const toggleScan = async () => {
    if (!nfcInitialized) {
      Alert.alert("NFC Not Ready", "NFC is not initialized or supported.");
      return;
    }
    if (isScanning) {
      await NfcService.stopTagReading();
      setIsScanning(false);
      setNfcStatus('Scanning stopped. Tap "Start Scanning" to resume.');
    } else {
      setIsScanning(true);
      setNfcStatus('Scanning for NFC tag... Hold tag near device.');
      await NfcService.startTagReading(handleTagDiscovered, handleScanError);
    }
  };

  const renderButton = () => {
    if (isLoading) return <ActivityIndicator size="large" color="#0000ff" />;
    if (!nfcInitialized && Platform.OS === 'android') return <Text>NFC Failed to Initialize</Text>;
    if (!nfcInitialized && Platform.OS !== 'android') return <Text>NFC Not Applicable</Text>;

    return (
      <Button
        title={isScanning ? 'Stop Scanning' : 'Start NFC Scan'}
        onPress={toggleScan}
        color={isScanning ? 'orange' : '#007AFF'}
        disabled={isLoading || !nfcInitialized}
      />
    );
  };

  return (
    <View style={styles.container}>
      <Text style={styles.header}>NFC Attendance</Text>
      <Text style={styles.statusText}>{nfcStatus}</Text>

      <View style={styles.modeSelector}>
        <TouchableOpacity
          style={[styles.modeButton, attendanceMode === 'entry' && styles.activeModeButton]}
          onPress={() => setAttendanceMode('entry')}
          disabled={isScanning || isLoading}>
          <Text style={[styles.modeButtonText, attendanceMode === 'entry' && styles.activeModeButtonText]}>
            Clock In
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.modeButton, attendanceMode === 'exit' && styles.activeModeButton]}
          onPress={() => setAttendanceMode('exit')}
          disabled={isScanning || isLoading}>
          <Text style={[styles.modeButtonText, attendanceMode === 'exit' && styles.activeModeButtonText]}>
            Clock Out
          </Text>
        </TouchableOpacity>
      </View>

      {renderButton()}

      {/* You might add a list of recent scans or other UI elements here */}
      {/* Example: <FlatList data={recentScans} renderItem={...} /> */}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
    backgroundColor: '#f5f5f5',
  },
  header: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 20,
  },
  statusText: {
    fontSize: 16,
    textAlign: 'center',
    marginVertical: 20,
    minHeight: 40, // Ensure space for messages
  },
  modeSelector: {
    flexDirection: 'row',
    marginBottom: 30,
  },
  modeButton: {
    flex: 1,
    paddingVertical: 12,
    paddingHorizontal: 20,
    marginHorizontal: 5,
    borderWidth: 1,
    borderColor: '#007AFF',
    borderRadius: 8,
    alignItems: 'center',
  },
  activeModeButton: {
    backgroundColor: '#007AFF',
  },
  modeButtonText: {
    color: '#007AFF',
    fontSize: 16,
  },
  activeModeButtonText: {
    color: '#fff',
  },
});

export default AttendanceScreen;