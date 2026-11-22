import { Trash2 } from "lucide-react";

function UserRow({
  user,
  currentUserId,
  onDelete,
  isAdmin,
  onRoleChange,
}) {
  const isCurrentUser = user.id === currentUserId;

  return (
    <tr className="border-b hover:bg-gray-50">

      <td className="px-6 py-4 font-medium text-gray-900">
        {user.name}
      </td>

      <td className="px-6 py-4 text-gray-600">
        {user.email}
      </td>

      <td className="px-6 py-4">
        {isAdmin ? (
          <select
            value={user.role}
            disabled={isCurrentUser}
            onChange={(e) => onRoleChange(user.id, e.target.value)}
            className={`rounded-lg border px-3 py-1.5 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-blue-500 ${
              isCurrentUser
                ? "bg-gray-100 text-gray-500 cursor-not-allowed"
                : "bg-white text-gray-800 cursor-pointer"
            }`}
            title={isCurrentUser ? "You cannot change your own role" : "Change user role"}
          >
            <option value="employee">Employee</option>
            <option value="manager">Manager</option>
            <option value="admin">Admin</option>
            {user.role === "super_admin" && (
              <option value="super_admin">Super Admin</option>
            )}
          </select>
        ) : (
          <span
            className={`px-3 py-1 rounded-full text-sm font-medium ${
              user.role === "admin"
                ? "bg-blue-100 text-blue-700"
                : user.role === "manager"
                ? "bg-yellow-100 text-yellow-700"
                : "bg-green-100 text-green-700"
            }`}
          >
            {user.role}
          </span>
        )}
      </td>

      <td className="px-6 py-4 text-right">
        {isCurrentUser ? (
          <span className="text-sm text-gray-400">
            You
          </span>
        ) : isAdmin ? (
          <button
            onClick={() => onDelete(user.id)}
            className="text-red-500 hover:text-red-700 p-1.5 rounded-lg hover:bg-red-50 transition"
            title="Delete user"
          >
            <Trash2 size={18} />
          </button>
        ) : (
          <span className="text-gray-400">
            —
          </span>
        )}
      </td>

    </tr>
  );
}

export default UserRow;
