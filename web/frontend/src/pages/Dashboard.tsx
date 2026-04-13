import { useState, useEffect } from "react";
import {
  Briefcase,
  TrendingUp,
  CalendarCheck,
  Clock,
  Loader2,
  AlertCircle,
} from "lucide-react";
import {
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { getApplicationStats, type ApplicationStats } from "@/lib/api";

const STATUS_COLORS: Record<string, string> = {
  Applied: "#3b82f6",
  Interview: "#22c55e",
  Offered: "#eab308",
  Rejected: "#ef4444",
  Withdrawn: "#6b7280",
  Saved: "#8b5cf6",
};

const STAT_CARDS = [
  {
    key: "total" as const,
    label: "Total Applications",
    icon: Briefcase,
    gradient: "from-blue-600/20 to-blue-800/10",
    text: "text-blue-400",
  },
  {
    key: "active" as const,
    label: "Active",
    icon: TrendingUp,
    gradient: "from-emerald-600/20 to-emerald-800/10",
    text: "text-emerald-400",
  },
  {
    key: "interviews" as const,
    label: "Interviews",
    icon: CalendarCheck,
    gradient: "from-amber-600/20 to-amber-800/10",
    text: "text-amber-400",
  },
  {
    key: "pending_followups" as const,
    label: "Pending Follow-ups",
    icon: Clock,
    gradient: "from-purple-600/20 to-purple-800/10",
    text: "text-purple-400",
  },
];

export default function Dashboard() {
  const [stats, setStats] = useState<ApplicationStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    getApplicationStats()
      .then((r) => setStats(r.data))
      .catch((e) => setError(e.message ?? "Failed to load stats"))
      .finally(() => setLoading(false));
  }, []);

  if (loading)
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-accent" />
      </div>
    );

  if (error)
    return (
      <div className="flex h-full items-center justify-center gap-2 text-red-400">
        <AlertCircle size={20} />
        <span>{error}</span>
      </div>
    );

  if (!stats) return null;

  const pieData = Object.entries(stats.by_status).map(([name, value]) => ({
    name,
    value,
  }));

  return (
    <div className="animate-fade-in space-y-6">
      <h2 className="text-2xl font-bold">Dashboard</h2>

      {/* Stat cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {STAT_CARDS.map(({ key, label, icon: Icon, gradient, text }) => (
          <div
            key={key}
            className={`rounded-xl border border-gray-800 bg-gradient-to-br ${gradient} p-5`}
          >
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-400">{label}</span>
              <Icon size={20} className={text} />
            </div>
            <p className={`mt-2 text-3xl font-bold ${text}`}>{stats[key]}</p>
          </div>
        ))}
      </div>

      {/* Charts */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Pie chart */}
        <div className="rounded-xl border border-gray-800 bg-gray-900 p-5">
          <h3 className="mb-4 font-semibold text-gray-200">Status Breakdown</h3>
          {pieData.length === 0 ? (
            <p className="py-12 text-center text-gray-500">No data yet</p>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={3}
                  dataKey="value"
                  label={({ name, percent }) =>
                    `${name} ${(percent * 100).toFixed(0)}%`
                  }
                >
                  {pieData.map((entry) => (
                    <Cell
                      key={entry.name}
                      fill={STATUS_COLORS[entry.name] ?? "#6b7280"}
                    />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#1e1e2a",
                    border: "1px solid #2a2a3a",
                    borderRadius: "0.5rem",
                    color: "#e4e4ec",
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Line chart */}
        <div className="rounded-xl border border-gray-800 bg-gray-900 p-5">
          <h3 className="mb-4 font-semibold text-gray-200">
            Applications Over Time
          </h3>
          {stats.by_date.length === 0 ? (
            <p className="py-12 text-center text-gray-500">No data yet</p>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={stats.by_date}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3a" />
                <XAxis
                  dataKey="date"
                  stroke="#7a7a96"
                  tick={{ fontSize: 12 }}
                />
                <YAxis stroke="#7a7a96" tick={{ fontSize: 12 }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#1e1e2a",
                    border: "1px solid #2a2a3a",
                    borderRadius: "0.5rem",
                    color: "#e4e4ec",
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="count"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  dot={{ fill: "#3b82f6", r: 4 }}
                  activeDot={{ r: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Recent activity */}
      <div className="rounded-xl border border-gray-800 bg-gray-900 p-5">
        <h3 className="mb-4 font-semibold text-gray-200">Recent Activity</h3>
        {stats.recent_activity.length === 0 ? (
          <p className="text-center text-gray-500">No recent activity</p>
        ) : (
          <ul className="divide-y divide-gray-800">
            {stats.recent_activity.map((a) => (
              <li
                key={a.id + a.timestamp}
                className="flex items-center justify-between py-3"
              >
                <div>
                  <span className="font-medium text-gray-200">
                    {a.company}
                  </span>
                  <span className="mx-2 text-gray-600">·</span>
                  <span className="text-sm text-gray-400">{a.role}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-sm text-accent">{a.action}</span>
                  <span className="text-xs text-gray-500">
                    {new Date(a.timestamp).toLocaleDateString()}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
