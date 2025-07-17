// c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\mobile_app\src\services\locationService.js
import { PermissionsAndroid, Platform } from 'react-native';
import Geolocation from 'react-native-geolocation-service';

export const requestLocationPermission = async () => {
  if (Platform.OS === 'ios') {
    // On iOS, permission is typically requested when you first try to access location.
    // You can also use libraries like react-native-permissions for more control.
    // For react-native-geolocation-service, it might prompt automatically or you can
    // call Geolocation.requestAuthorization("whenInUse"); or "always"
    try {
      const authLevel = await Geolocation.requestAuthorization('whenInUse');
      return authLevel === 'granted';
    } catch (error) {
      console.error('iOS Location permission request error:', error);
      return false;
    }
  }

  if (Platform.OS === 'android') {
    try {
      const granted = await PermissionsAndroid.request(
        PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION,
        {
          title: 'Location Access Required',
          message: 'This app needs to access your location for [Your Feature, e.g., attendance verification].',
          buttonNeutral: 'Ask Me Later',
          buttonNegative: 'Cancel',
          buttonPositive: 'OK',
        },
      );
      return granted === PermissionsAndroid.RESULTS.GRANTED;
    } catch (err) {
      console.warn(err);
      return false;
    }
  }
  return false; // Should not happen
};

export const getCurrentLocation = () => {
  return new Promise((resolve, reject) => {
    Geolocation.getCurrentPosition(
      (position) => {
        resolve(position.coords);
      },
      (error) => {
        console.log('getCurrentLocation error:', error.code, error.message);
        reject(error);
      },
      {
        enableHighAccuracy: true, // Try to get a more accurate position
        timeout: 15000,         // Stop trying after 15 seconds
        maximumAge: 10000,        // Use a cached position if it's no older than 10 seconds
        // distanceFilter: 0,     // For watchPosition: minimum displacement in meters
        // showLocationDialog: true // Android only: show a dialog if location is disabled
      }
    );
  });
};