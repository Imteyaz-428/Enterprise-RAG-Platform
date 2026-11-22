import { useEffect, useMemo, useState, useCallback } from "react";
import { Search } from "lucide-react";
import toast from "react-hot-toast";

import Layout from "../../components/layout/Layout";
import PageHeader from "../../components/common/PageHeader";
import DocumentTable from "../../components/document/DocumentTable";
import { useAuth } from "../../context/useAuth";
import { hasRole } from "../../utils/roles";

import {
  getDocuments,
  deleteDocument,
} from "../../services/document";

function Documents() {
  const { user } = useAuth();
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("all");

  const [currentPage, setCurrentPage] = useState(1);

  const documentsPerPage = 8;

  const loadDocuments = useCallback(async (showSkeleton = false) => {
    if (showSkeleton) setLoading(true);
    try {
      const data = await getDocuments();
      setDocuments(data);
    } catch {
      toast.error("Failed to load documents");
    } finally {
      if (showSkeleton) setLoading(false);
    }
  }, []);

  useEffect(() => {
    let ignore = false;
    async function load() {
      try {
        const data = await getDocuments();
        if (!ignore) {
          setDocuments(data);
        }
      } catch {
        toast.error("Failed to load documents");
      } finally {
        if (!ignore) {
          setLoading(false);
        }
      }
    }
    load();
    return () => {
      ignore = true;
    };
  }, []);

  // Poll GET /documents every 3s only while some document has status "processing"
  useEffect(() => {
    const hasProcessing = documents.some((doc) => doc.status === "processing");
    if (!hasProcessing) return;

    const interval = setInterval(() => {
      loadDocuments(false);
    }, 3000);

    return () => clearInterval(interval);
  }, [documents, loadDocuments]);

  const handleDelete = async (id) => {
    if (!window.confirm("Delete this document?")) {
      return;
    }

    try {
      await deleteDocument(id);
      toast.success("Document deleted");
      loadDocuments(false);
    } catch {
      toast.error("Failed to delete document");
    }
  };

  const handleSearchChange = (e) => {
    setSearch(e.target.value);
    setCurrentPage(1);
  };

  const handleStatusChange = (e) => {
    setStatus(e.target.value);
    setCurrentPage(1);
  };

  const filteredDocuments = useMemo(() => {
    return documents.filter((doc) => {
      const matchSearch =
        doc.original_filename
          .toLowerCase()
          .includes(search.toLowerCase()) ||
        doc.title
          .toLowerCase()
          .includes(search.toLowerCase());

      const matchStatus =
        status === "all" ||
        doc.status === status;

      return matchSearch && matchStatus;
    });
  }, [documents, search, status]);

  const totalPages = Math.ceil(
    filteredDocuments.length / documentsPerPage
  );

  const startIndex =
    (currentPage - 1) * documentsPerPage;

  const paginatedDocuments =
    filteredDocuments.slice(
      startIndex,
      startIndex + documentsPerPage
    );

  const canDelete = hasRole(user, "manager");

  return (
    <Layout>
      <PageHeader
        title="Documents"
        subtitle="Manage your organization's knowledge base."
      />

      <div className="bg-white border rounded-xl shadow-sm p-5 mb-6">
        <div className="grid md:grid-cols-2 gap-4">
          <div className="relative">
            <Search
              size={18}
              className="absolute left-3 top-3.5 text-gray-400"
            />

            <input
              type="text"
              placeholder="Search documents..."
              value={search}
              onChange={handleSearchChange}
              className="w-full rounded-lg border pl-10 pr-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <select
            value={status}
            onChange={handleStatusChange}
            className="rounded-lg border px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All Status</option>
            <option value="completed">Completed</option>
            <option value="processing">Processing</option>
            <option value="failed">Failed</option>
          </select>
        </div>
      </div>

      {loading ? (
        <div className="bg-white rounded-xl border shadow-sm p-6 space-y-4">
          <div className="h-6 bg-gray-200 rounded w-1/4 animate-pulse" />
          <div className="divide-y">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="py-4 flex items-center justify-between animate-pulse">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 bg-gray-200 rounded-lg" />
                  <div className="space-y-2">
                    <div className="w-48 h-4 bg-gray-200 rounded" />
                    <div className="w-32 h-3 bg-gray-100 rounded" />
                  </div>
                </div>
                <div className="w-20 h-6 bg-gray-200 rounded-full" />
              </div>
            ))}
          </div>
        </div>
      ) : (
        <DocumentTable
          documents={paginatedDocuments}
          totalDocuments={filteredDocuments.length}
          currentPage={currentPage}
          totalPages={totalPages}
          setCurrentPage={setCurrentPage}
          onDelete={handleDelete}
          canDelete={canDelete}
        />
      )}
    </Layout>
  );
}

export default Documents;
