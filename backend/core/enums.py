from enum import Enum

class UserRole(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    EMPLOYEE = "employee"
    SUPER_ADMIN = "super_admin"

# Alias to represent standard User role
UserRole.USER = UserRole.EMPLOYEE
