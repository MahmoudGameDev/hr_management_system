import NfcManager, {NfcEvents, NfcTech, NdefParser} from 'react-native-nfc-manager';
import {Platform} from 'react-native';

class NfcService {
  constructor() {
    this.isInitialized = false;
    this.isListenerRegistered = false;
  }

  async init() {
    if (Platform.OS !== 'android') {
      console.log('NFC Service: NFC is primarily supported on Android for this type of usage.');
      return false;
    }
    try {
      const isSupported = await NfcManager.isSupported();
      if (!isSupported) {
        console.warn('NFC Service: NFC is not supported on this device.');
        this.isInitialized = false;
        return false;
      }
      await NfcManager.start();
      this.isInitialized = true;
      console.log('NFC Service: NFC Manager started successfully.');
      return true;
    } catch (ex) {
      console.warn('NFC Service: Error starting NFC Manager', ex);
      this.isInitialized = false;
      // You might want to throw a custom error or return a specific status
      throw new Error('Failed to initialize NFC. Is it enabled in device settings?');
    }
  }

  async startTagReading(onTagDiscoveredCallback, onErrorCallback) {
    if (!this.isInitialized) {
      console.warn('NFC Service: NFC not initialized. Call init() first.');
      if (onErrorCallback) onErrorCallback('NFC_NOT_INITIALIZED');
      return;
    }

    try {
      // Register for NDEF technology
      await NfcManager.requestTechnology(NfcTech.Ndef);
      console.log('NFC Service: NDEF technology requested. Waiting for tag...');

      if (this.isListenerRegistered) {
        NfcManager.setEventListener(NfcEvents.DiscoverTag, null); // Clear previous listener
      }

      NfcManager.setEventListener(NfcEvents.DiscoverTag, (tag) => {
        console.log('NFC Service: Tag Discovered:', JSON.stringify(tag));
        let tagId = tag.id; // Usually the UID

        // Attempt to parse NDEF message if available
        let ndefMessage = '';
        if (tag.ndefMessage && tag.ndefMessage.length > 0) {
          ndefMessage = NdefParser.parseText(tag.ndefMessage[0]); // Example: parsing first text record
          console.log('NFC Service: NDEF Message:', ndefMessage);
        }

        if (onTagDiscoveredCallback) {
          onTagDiscoveredCallback(tagId, ndefMessage, tag);
        }
        // It's often good practice to cancel the request after a tag is found
        // if you only expect one scan at a time.
        // this.stopTagReading(); // Or let the calling component decide
      });
      this.isListenerRegistered = true;
    } catch (ex) {
      console.warn('NFC Service: Error requesting NFC technology or setting listener', ex);
      // NfcManager.cancelTechnologyRequest().catch(() => 0); // Clean up
      if (onErrorCallback) onErrorCallback('NFC_SCAN_ERROR', ex);
    }
  }

  async stopTagReading() {
    if (!this.isInitialized) {
      return;
    }
    try {
      if (this.isListenerRegistered) {
        NfcManager.setEventListener(NfcEvents.DiscoverTag, null);
        this.isListenerRegistered = false;
      }
      await NfcManager.cancelTechnologyRequest();
      console.log('NFC Service: NFC tag reading stopped and technology request cancelled.');
    } catch (ex) {
      console.warn('NFC Service: Error stopping NFC tag reading or cancelling technology request', ex);
    }
  }

  // Call this when the component unmounts or NFC is no longer needed
  async cleanup() {
    if (!this.isInitialized) {
      return;
    }
    await this.stopTagReading(); // Ensure listener and request are cancelled
    // Note: NfcManager.stop() might not be necessary or available depending on library version.
    // Typically, cancelling requests and removing listeners is sufficient.
    console.log('NFC Service: Cleaned up.');
  }
}

export default new NfcService();