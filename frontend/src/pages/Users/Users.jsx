import { useEffect, useState, useCallback } from "react";
import toast from "react-hot-toast";

import Layout from "../../components/layout/Layout";
import UserTable from "../../components/users/UserTable";
import AddUserModal from "../../components/users/AddUserModal";
import { useAuth } from "../../context/useAuth";
import { hasRole } from "../../utils/roles";

import {
  getUsers,
  createUser,
  deleteUser,
  updateUser,
} from "../../services/user";

function Users() {
  const { user: currentUser, loading: authLoading } = useAuth();
  const [users, setUsers] = useState([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  const isAdmin = hasRole(currentUser, "admin");

  const loadUsers = useCallback(async () => {
    try {
      const data = await getUsers();
      setUsers(data);
    } catch {
      toast.error("Failed to load users");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let ignore = false;
    async function load() {
      if (isAdmin) {
        try {
          const data = await getUsers();
          if (!ignore) {
            setUsers(data);
          }
        } catch {
          toast.error("Failed to load users");
        } finally {
          if (!ignore) {
            setLoading(false);
          }
        }
      } else if (!authLoading) {
        if (!ignore) {
          setLoading(false);
        }
      }
    }
    load();
    return () => {
      ignore = true;
    };
  }, [isAdmin, authLoading]);

  const handleCreate = async (form) => {
    try {
      await createUser(form);
      toast.success("User created");
      loadUsers();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to create user");
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Delete this user?")) {
      return;
    }

    try {
      await deleteUser(id);
      toast.success("User deleted");
      loadUsers();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to delete user");
    }
  };

  const handleRoleChange = async (userId, newRole) => {
    const targetUser = users.find((u) => u.id === userId);
    if (!targetUser || targetUser.role === newRole) return;

    const previousRole = targetUser.role;

    // Optimistic UI update
    setUsers((prev) =>
      prev.map((u) => (u.id === userId ? { ...u, role: newRole } : u))
    );

    try {
      await updateUser(userId, { role: newRole });
      toast.success("Role updated successfully.");
    } catch (err) {
      // Rollback on failure
      setUsers((prev) =>
        prev.map((u) => (u.id === userId ? { ...u, role: previousRole } : u))
      );
      toast.error(err.response?.data?.detail || "Failed to update role");
    }
  };

  if (authLoading || loading) {
    return (
      <Layout>
        <div className="text-center py-20 text-gray-500 font-medium">
          Loading team members...
        </div>
      </Layout>
    );
  }

  if (!isAdmin) {
    return (
      <Layout>
        <div className="bg-white rounded-xl shadow p-10 text-center">
          <h2 className="text-2xl font-bold mb-3">
            Access Denied
          </h2>

          <p className="text-gray-500">
            Only organization administrators can manage team members.
          </p>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold">
            Team Members
          </h1>

          <p className="text-gray-500 mt-2">
            Manage users in your organization.
          </p>
        </div>

        <button
          onClick={() => setOpen(true)}
          className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-3 rounded-lg font-medium transition shadow-sm"
        >
          Add User
        </button>
      </div>

      <UserTable
        users={users}
        currentUserId={currentUser?.id}
        isAdmin={isAdmin}
        onDelete={handleDelete}
        onRoleChange={handleRoleChange}
      />

      <AddUserModal
        open={open}
        onClose={() => setOpen(false)}
        onCreate={handleCreate}
      />
    </Layout>
  );
}

export default Users;
