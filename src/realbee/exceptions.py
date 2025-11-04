"""
Custom exceptions for real-bee framework
"""


class RealBeeException(Exception):
    """Base exception for real-bee framework"""
    pass


class EntityNotFoundException(RealBeeException):
    """Raised when an entity is not found"""
    pass


class ValidationException(RealBeeException):
    """Raised when validation fails"""
    pass


class SearchException(RealBeeException):
    """Raised when search operations fail"""
    pass


class WebSocketException(RealBeeException):
    """Raised when WebSocket operations fail"""
    pass


class DatabaseException(RealBeeException):
    """Raised when database operations fail"""
    pass


class CacheException(RealBeeException):
    """Raised when cache operations fail"""
    pass


class EventBusException(RealBeeException):
    """Raised when event bus operations fail"""
    pass
