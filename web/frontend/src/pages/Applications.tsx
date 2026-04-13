import { useState, useEffect, useCallback } from "react";
import {
  Loader2,
  AlertCircle,
  X,
  ExternalLink,
  ChevronDown,
} from "lucide-react";
import {
  getApplications,
  getApplication,
  updateApplicationStatus,
  type Application,
} from "@/lib/api";

const STATUSES = [
  "All",
  "Applied",
  "Interview",
  "Offered",
  "Rejected",
  "Withdrawn",
  "Saved",
];

const STATUS_STYLES: Record<string, string> = {
  Applied: "bg-blue-500/15 text-blue-400",
  Interview: "bg-emerald-500/15 text-emerald-400",
  Offered: "bg-amber-500/15 text-amber-400",
  Rejected: "bg-red-500/15 text-red-400",
  Withdrawn: "bg-gray-500/15 text-gray-400",
  Saved: "bg-purple-500/15 text-purple-400",
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${
        STATUS_STYLES[status] ?? "bg-gray-700 text-gray-300"
      }`}
    >
      {status}
    </span>
  );
}

export default function Applications() {
  const [apps, setApps] = useState<Application[]>([]);
  const [filter, setFilter] = useState("All");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [selected, setSelected] = useState<Application | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [newStatus, setNewStatus] = useState("");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    getApplications(filter === "All" ? undefined : filter)
      .then((r) => setApps(r.data))
      .catch((e) => setError(e.message ?? "Failed to load"))
      .finally(() => setLoading(false));
  }, [filter]);

  useEffect(() => {
    load();
  }, [load]);

  const openDetail = (id: string) => {
    setDetailLoading(true);
    getApplication(id)
      .then((r) => {
        setSelected(r.data);
        setNewStatus(r.data.status);
        setNotes(r.data.notes ?? "");
      })
      .catch(() => setError("Failed to load detail"))
      .finally(() => setDetailLoading(false));
  };

  const saveStatus = async () => {
    if (!selected) return;
    setSaving(true);
    try {
      await updateApplicationStatus(selected.id, {
        status: newStatus,
        notes,
      });
      setSelected({ ...selected, status: newStatus, notes });
      load();
    } catch {
      setError("Failed to update status");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="animate-fade-in space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Applications</h2>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        {STATUSES.map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
              filter === s
                ? "bg-accent text-white"
                : "bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-gray-200"
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {/* Table */}
      {loading ? (
        <div className="flex justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-accent" />
        </div>
      ) : error ? (
        <div className="flex items-center justify-center gap-2 py-20 text-red-400">
          <AlertCircle size={20} />
          <span>{error}</span>
        </div>
      ) : apps.length === 0 ? (
        <p className="py-20 text-center text-gray-500">
          No applications found.
        </p>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-gray-800">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-gray-800 bg-gray-900 text-xs uppercase text-gray-500">
              <tr>
                <th className="px-4 py-3">ID</th>
                <th className="px-4 py-3">Company</th>
                <th className="px-4 py-3">Role</th>
                <th className="px-4 py-3">Platform</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Applied</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {apps.map((app) => (
                <tr
                  key={app.id}
                  onClick={() => openDetail(app.id)}
                  className="cursor-pointer bg-gray-900/50 transition-colors hover:bg-gray-800/60"
                >
                  <td className="whitespace-nowrap px-4 py-3 font-mono text-xs text-gray-500">
                    {app.id.slice(0, 8)}
                  </td>
                  <td className="px-4 py-3 font-medium text-gray-200">
                    {app.company}
                  </td>
                  <td className="px-4 py-3 text-gray-300">{app.role}</td>
                  <td className="px-4 py-3">
                    <span className="rounded bg-gray-800 px-2 py-0.5 text-xs text-gray-300">
                      {app.platform}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={app.status} />
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-gray-400">
                    {new Date(app.applied_date).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Detail modal */}
      {(selected || detailLoading) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="mx-4 w-full max-w-lg animate-fade-in rounded-2xl border border-gray-800 bg-gray-900 p-6">
            {detailLoading ? (
              <div className="flex justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-accent" />
              </div>
            ) : selected ? (
              <>
                <div className="mb-4 flex items-start justify-between">
                  <div>
                    <h3 className="text-xl font-bold text-gray-100">
                      {selected.company}
                    </h3>
                    <p className="text-sm text-gray-400">{selected.role}</p>
                  </div>
                  <button
                    onClick={() => setSelected(null)}
                    className="rounded-lg p-1 text-gray-500 hover:bg-gray-800 hover:text-gray-200"
                  >
                    <X size={20} />
                  </button>
                </div>

                <div className="mb-4 grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <span className="text-gray-500">Platform</span>
                    <p className="text-gray-200">{selected.platform}</p>
                  </div>
                  <div>
                    <span className="text-gray-500">Applied</span>
                    <p className="text-gray-200">
                      {new Date(selected.applied_date).toLocaleDateString()}
                    </p>
                  </div>
                  {selected.location && (
                    <div>
                      <span className="text-gray-500">Location</span>
                      <p className="text-gray-200">{selected.location}</p>
                    </div>
                  )}
                  {selected.salary && (
                    <div>
                      <span className="text-gray-500">Salary</span>
                      <p className="text-gray-200">{selected.salary}</p>
                    </div>
                  )}
                </div>

                {selected.url && (
                  <a
                    href={selected.url}
                    target="_blank"
                    rel="noreferrer"
                    className="mb-4 inline-flex items-center gap-1 text-sm text-accent hover:underline"
                  >
                    View posting <ExternalLink size={14} />
                  </a>
                )}

                {/* Status select */}
                <div className="mb-4">
                  <label className="mb-1 block text-sm text-gray-400">
                    Status
                  </label>
                  <div className="relative">
                    <select
                      value={newStatus}
                      onChange={(e) => setNewStatus(e.target.value)}
                      className="w-full appearance-none rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-200 focus:border-accent focus:outline-none"
                    >
                      {STATUSES.filter((s) => s !== "All").map((s) => (
                        <option key={s}>{s}</option>
                      ))}
                    </select>
                    <ChevronDown
                      size={16}
                      className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-gray-500"
                    />
                  </div>
                </div>

                {/* Notes */}
                <div className="mb-4">
                  <label className="mb-1 block text-sm text-gray-400">
                    Notes
                  </label>
                  <textarea
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    rows={4}
                    className="w-full resize-none rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-200 placeholder-gray-600 focus:border-accent focus:outline-none"
                    placeholder="Add notes about this application..."
                  />
                </div>

                <button
                  onClick={saveStatus}
                  disabled={saving}
                  className="w-full rounded-lg bg-accent px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-accent-hover disabled:opacity-50"
                >
                  {saving ? "Saving..." : "Save Changes"}
                </button>
              </>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}
