import UserRow from "./UserRow";
import EmptyUsers from "./EmptyUsers";

function UserTable({
  users,
  currentUserId,
  onDelete,
  isAdmin,
  onRoleChange,
}) {

  if (users.length === 0) {
    return <EmptyUsers />;
  }

  return (
    <div className="bg-white rounded-xl shadow overflow-hidden">

      <table className="w-full">

        <thead className="bg-gray-100">

          <tr>

            <th className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wider text-gray-600">
              Name
            </th>

            <th className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wider text-gray-600">
              Email
            </th>

            <th className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wider text-gray-600">
              Role
            </th>

            <th className="px-6 py-4 text-right text-xs font-semibold uppercase tracking-wider text-gray-600">
              Action
            </th>

          </tr>

        </thead>

        <tbody className="divide-y divide-gray-200">

          {users.map((user) => (
            <UserRow
              key={user.id}
              user={user}
              currentUserId={currentUserId}
              onDelete={onDelete}
              isAdmin={isAdmin}
              onRoleChange={onRoleChange}
            />
          ))}

        </tbody>

      </table>

    </div>
  );
}

export default UserTable;
