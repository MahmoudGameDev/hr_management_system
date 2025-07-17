// c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\mobile_app\src\services\database.js
import SQLite from 'react-native-sqlite-storage';

SQLite.enablePromise(true); // Enable promise-based interface

const DATABASE_NAME = 'HRApp.db';
const DATABASE_LOCATION = 'default';

let db;

export const openDatabase = async () => {
  if (db) {
    return db; // Return existing db connection if already open
  }
  try {
    db = await SQLite.openDatabase({
      name: DATABASE_NAME,
      location: DATABASE_LOCATION,
    });
    console.log('Database opened successfully');
    await initDB(db);
    return db;
  } catch (error) {
    console.error('Failed to open database', error);
    throw error;
  }
};

const initDB = async (dbInstance) => {
  // Create tables if they don't exist
  const queryLeaveRequests = `
    CREATE TABLE IF NOT EXISTS leave_requests (
      id INTEGER PRIMARY KEY NOT NULL,
      leave_type_id INTEGER,
      leave_type_name TEXT, 
      start_date TEXT NOT NULL,
      end_date TEXT NOT NULL,
      reason TEXT,
      status TEXT NOT NULL,
      submission_date TEXT 
      -- Add other relevant fields from your API response
    );`;
  try {
    await dbInstance.executeSql(queryLeaveRequests);
    console.log('leave_requests table created or already exists.');
    // Add other table creations here (e.g., leave_types)
  } catch (error) {
    console.error('Error creating leave_requests table', error);
    throw error;
  }
};

export const getCachedLeaveRequests = async () => {
  const dbInstance = await openDatabase();
  try {
    const [results] = await dbInstance.executeSql('SELECT * FROM leave_requests ORDER BY submission_date DESC;');
    const requests = [];
    for (let i = 0; i < results.rows.length; i++) {
      requests.push(results.rows.item(i));
    }
    return requests;
  } catch (error) {
    console.error('Error fetching cached leave requests', error);
    return []; // Return empty array on error
  }
};

export const cacheLeaveRequests = async (requestsToCache) => {
  if (!requestsToCache || requestsToCache.length === 0) return;
  const dbInstance = await openDatabase();
  try {
    // Clear old requests before caching new ones for simplicity in this example
    // A more sophisticated approach might involve upserting or diffing.
    await dbInstance.executeSql('DELETE FROM leave_requests;');
    console.log('Old leave requests cleared from cache.');

    for (const req of requestsToCache) {
      // Ensure your API response for leave_type is handled (e.g. req.leave_type.name)
      const query = `INSERT INTO leave_requests (id, leave_type_id, leave_type_name, start_date, end_date, reason, status, submission_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?);`;
      await dbInstance.executeSql(query, [req.id, req.leave_type?.id, req.leave_type?.name, req.start_date, req.end_date, req.reason, req.status, req.submission_date || new Date().toISOString()]);
    }
    console.log(`${requestsToCache.length} leave requests cached successfully.`);
  } catch (error) {
    console.error('Error caching leave requests', error);
  }
};

// Add functions for other tables like getCachedLeaveTypes, cacheLeaveTypes etc.