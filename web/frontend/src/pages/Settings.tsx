import { useEffect, useState } from "react";
import {
  Save,
  Loader2,
  AlertCircle,
  CheckCircle2,
  UserCircle,
  SlidersHorizontal,
  Link2,
} from "lucide-react";
import {
  getProfile,
  updateProfile,
  getPreferences,
  updatePreferences,
  getConnections,
  type Profile,
  type Preferences,
  type ConnectionStatus,
} from "@/lib/api";

function useAutoFeedback() {
  const [msg, setMsg] = useState("");
  const show = (text: string) => {
    setMsg(text);
    setTimeout(() => setMsg(""), 3000);
  };
  return { msg, show };
}

export default function Settings() {
  const [profile, setProfile] = useState<Profile>({
    name: "",
    email: "",
    phone: "",
    location: "",
    linkedin: "",
    github: "",
  });
  const [prefs, setPrefs] = useState<Preferences>({
    target_roles: [],
    target_locations: [],
    min_salary: 0,
    max_salary: 0,
    remote_only: false,
    followup_days: 7,
    auto_sync: true,
  });
  const [connections, setConnections] = useState<ConnectionStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [savingProfile, setSavingProfile] = useState(false);
  const [savingPrefs, setSavingPrefs] = useState(false);
  const profileFeedback = useAutoFeedback();
  const prefsFeedback = useAutoFeedback();

  useEffect(() => {
    Promise.all([getProfile(), getPreferences(), getConnections()])
      .then(([p, pr, c]) => {
        setProfile(p.data);
        setPrefs(pr.data);
        setConnections(c.data);
      })
      .catch((e) => setError(e.message ?? "Failed to load settings"))
      .finally(() => setLoading(false));
  }, []);

  const saveProfile = async () => {
    setSavingProfile(true);
    try {
      await updateProfile(profile);
      profileFeedback.show("Profile saved!");
    } catch {
      profileFeedback.show("Failed to save profile");
    } finally {
      setSavingProfile(false);
    }
  };

  const savePrefs = async () => {
    setSavingPrefs(true);
    try {
      await updatePreferences(prefs);
      prefsFeedback.show("Preferences saved!");
    } catch {
      prefsFeedback.show("Failed to save preferences");
    } finally {
      setSavingPrefs(false);
    }
  };

  if (loading)
    return (
      <div className="flex h-96 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-accent" />
      </div>
    );

  if (error)
    return (
      <div className="flex h-96 flex-col items-center justify-center gap-3 text-red-400">
        <AlertCircle className="h-10 w-10" />
        <p className="text-sm">{error}</p>
      </div>
    );

  return (
    <div className="animate-fade-in space-y-8">
      {/* Profile */}
      <section className="rounded-xl border border-gray-800 bg-gray-900 p-6">
        <div className="mb-5 flex items-center gap-2">
          <UserCircle className="h-5 w-5 text-accent" />
          <h2 className="text-sm font-semibold text-gray-200">Profile</h2>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {(
            [
              ["name", "Full Name"],
              ["email", "Email"],
              ["phone", "Phone"],
              ["location", "Location"],
              ["linkedin", "LinkedIn URL"],
              ["github", "GitHub URL"],
            ] as const
          ).map(([key, label]) => (
            <div key={key}>
              <label className="mb-1.5 block text-xs font-medium text-gray-500">
                {label}
              </label>
              <input
                type="text"
                value={profile[key] ?? ""}
                onChange={(e) =>
                  setProfile({ ...profile, [key]: e.target.value })
                }
                className="w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-200 outline-none focus:border-accent"
              />
            </div>
          ))}
        </div>

        <div className="mt-5 flex items-center gap-3">
          <button
            onClick={saveProfile}
            disabled={savingProfile}
            className="flex items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-hover disabled:opacity-50"
          >
            {savingProfile ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            Save Profile
          </button>
          {profileFeedback.msg && (
            <span
              className={`flex items-center gap-1 text-sm ${
                profileFeedback.msg.includes("saved")
                  ? "text-emerald-400"
                  : "text-red-400"
              }`}
            >
              <CheckCircle2 className="h-4 w-4" />
              {profileFeedback.msg}
            </span>
          )}
        </div>
      </section>

      {/* Preferences */}
      <section className="rounded-xl border border-gray-800 bg-gray-900 p-6">
        <div className="mb-5 flex items-center gap-2">
          <SlidersHorizontal className="h-5 w-5 text-accent" />
          <h2 className="text-sm font-semibold text-gray-200">Preferences</h2>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div>
            <label className="mb-1.5 block text-xs font-medium text-gray-500">
              Target Roles (comma-separated)
            </label>
            <input
              type="text"
              value={prefs.target_roles.join(", ")}
              onChange={(e) =>
                setPrefs({
                  ...prefs,
                  target_roles: e.target.value
                    .split(",")
                    .map((s) => s.trim())
                    .filter(Boolean),
                })
              }
              className="w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-200 outline-none focus:border-accent"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-gray-500">
              Target Locations (comma-separated)
            </label>
            <input
              type="text"
              value={prefs.target_locations.join(", ")}
              onChange={(e) =>
                setPrefs({
                  ...prefs,
                  target_locations: e.target.value
                    .split(",")
                    .map((s) => s.trim())
                    .filter(Boolean),
                })
              }
              className="w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-200 outline-none focus:border-accent"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-gray-500">
              Min Salary
            </label>
            <input
              type="number"
              value={prefs.min_salary}
              onChange={(e) =>
                setPrefs({ ...prefs, min_salary: Number(e.target.value) })
              }
              className="w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-200 outline-none focus:border-accent"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-gray-500">
              Max Salary
            </label>
            <input
              type="number"
              value={prefs.max_salary}
              onChange={(e) =>
                setPrefs({ ...prefs, max_salary: Number(e.target.value) })
              }
              className="w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-200 outline-none focus:border-accent"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-gray-500">
              Follow-up After (days)
            </label>
            <input
              type="number"
              value={prefs.followup_days}
              onChange={(e) =>
                setPrefs({ ...prefs, followup_days: Number(e.target.value) })
              }
              className="w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-200 outline-none focus:border-accent"
            />
          </div>
          <div className="flex flex-col gap-3 pt-5">
            <label className="flex cursor-pointer items-center gap-2 text-sm text-gray-300">
              <input
                type="checkbox"
                checked={prefs.remote_only}
                onChange={(e) =>
                  setPrefs({ ...prefs, remote_only: e.target.checked })
                }
                className="accent-accent"
              />
              Remote Only
            </label>
            <label className="flex cursor-pointer items-center gap-2 text-sm text-gray-300">
              <input
                type="checkbox"
                checked={prefs.auto_sync}
                onChange={(e) =>
                  setPrefs({ ...prefs, auto_sync: e.target.checked })
                }
                className="accent-accent"
              />
              Auto-sync Gmail
            </label>
          </div>
        </div>

        <div className="mt-5 flex items-center gap-3">
          <button
            onClick={savePrefs}
            disabled={savingPrefs}
            className="flex items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-hover disabled:opacity-50"
          >
            {savingPrefs ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            Save Preferences
          </button>
          {prefsFeedback.msg && (
            <span
              className={`flex items-center gap-1 text-sm ${
                prefsFeedback.msg.includes("saved")
                  ? "text-emerald-400"
                  : "text-red-400"
              }`}
            >
              <CheckCircle2 className="h-4 w-4" />
              {prefsFeedback.msg}
            </span>
          )}
        </div>
      </section>

      {/* Connections */}
      <section className="rounded-xl border border-gray-800 bg-gray-900 p-6">
        <div className="mb-5 flex items-center gap-2">
          <Link2 className="h-5 w-5 text-accent" />
          <h2 className="text-sm font-semibold text-gray-200">Connections</h2>
        </div>

        {connections.length > 0 ? (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {connections.map((c) => (
              <div
                key={c.name}
                className="flex items-center gap-3 rounded-lg border border-gray-800 bg-gray-850 px-4 py-3"
              >
                <span
                  className={`h-2.5 w-2.5 rounded-full ${
                    c.connected ? "bg-emerald-400" : "bg-gray-600"
                  }`}
                />
                <div>
                  <p className="text-sm font-medium text-gray-200">{c.name}</p>
                  <p className="text-xs text-gray-500">
                    {c.connected
                      ? c.last_sync
                        ? `Synced ${new Date(c.last_sync).toLocaleDateString()}`
                        : "Connected"
                      : "Not connected"}
                  </p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-500">No connections configured</p>
        )}
      </section>
    </div>
  );
}
