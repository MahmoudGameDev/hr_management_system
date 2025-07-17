# c:\Users\mahmo\OneDrive\Documents\ai\HR\version\utils\exceptions.py

class HRException(Exception):
    """Base class for exceptions in this module."""
    pass


class InvalidInputError(HRException):
    """Exception raised for errors in the input data."""
    pass

class EmployeeNotFoundError(HRException):
    """Exception raised when an employee is not found."""
    pass

class DepartmentNotFoundError(HRException):
    """Exception raised when a department is not found."""
    pass

class DatabaseOperationError(HRException):
    """Exception raised for errors during database operations."""
    pass

class AttendanceError(HRException):
    """Base class for attendance related errors."""
    pass

class AlreadyClockedInError(AttendanceError):
    """Raised when trying to clock in while already clocked in."""
    pass

class NotClockedInError(AttendanceError):
    """Raised when trying to clock out without an open clock-in record."""
    pass

class UserNotFoundError(HRException): # Assuming you might want this for user management
    """Exception raised when a user is not found."""
    pass