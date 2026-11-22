export const ROLE_HIERARCHY = {
  super_admin: 4,
  admin: 3,
  manager: 2,
  employee: 1,
};

/**
 * Checks if a user meets the minimum required role.
 * Role order: super_admin > admin > manager > employee
 *
 * @param {Object|string} user - User object with `role` property, or role string
 * @param {string} minRole - Minimum role required
 * @returns {boolean}
 */
export function hasRole(user, minRole) {
  if (!user || !minRole) return false;
  const userRole = (typeof user === "string" ? user : user.role || "")
    .trim()
    .toLowerCase();
  const targetRole = minRole.trim().toLowerCase();

  const userLevel = ROLE_HIERARCHY[userRole] || 0;
  const minLevel = ROLE_HIERARCHY[targetRole] || 0;

  if (minLevel === 0) return false;
  return userLevel >= minLevel;
}
