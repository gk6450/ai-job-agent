import { useState } from "react";
import {
  Search,
  MapPin,
  Loader2,
  ExternalLink,
  Building2,
  AlertCircle,
} from "lucide-react";
import { searchJobs, type JobResult, type SearchParams } from "@/lib/api";

const PLATFORMS = ["LinkedIn", "Naukri", "Indeed", "Glassdoor"];

export default function JobSearch() {
  const [form, setForm] = useState<SearchParams>({
    keywords: "",
    location: "",
    platforms: [],
    experience_level: "mid",
    remote_only: false,
  });
  const [results, setResults] = useState<JobResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [searched, setSearched] = useState(false);

  const togglePlatform = (p: string) => {
    setForm((f) => ({
      ...f,
      platforms: f.platforms.includes(p)
        ? f.platforms.filter((x) => x !== p)
        : [...f.platforms, p],
    }));
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.keywords.trim()) return;
    setLoading(true);
    setError("");
    setSearched(true);
    try {
      const r = await searchJobs(form);
      setResults(r.data.results ?? []);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Search failed";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="animate-fade-in space-y-6">
      <h2 className="text-2xl font-bold">Job Search</h2>

      {/* Search form */}
      <form
        onSubmit={handleSearch}
        className="rounded-xl border border-gray-800 bg-gray-900 p-5 space-y-4"
      >
        <div className="grid gap-4 md:grid-cols-2">
          {/* Keywords */}
          <div className="relative">
            <Search
              size={16}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500"
            />
            <input
              type="text"
              placeholder="Keywords (e.g. React Developer)"
              value={form.keywords}
              onChange={(e) =>
                setForm((f) => ({ ...f, keywords: e.target.value }))
              }
              className="w-full rounded-lg border border-gray-700 bg-gray-800 py-2.5 pl-10 pr-3 text-sm text-gray-200 placeholder-gray-500 focus:border-accent focus:outline-none"
            />
          </div>

          {/* Location */}
          <div className="relative">
            <MapPin
              size={16}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500"
            />
            <input
              type="text"
              placeholder="Location (e.g. Bangalore)"
              value={form.location}
              onChange={(e) =>
                setForm((f) => ({ ...f, location: e.target.value }))
              }
              className="w-full rounded-lg border border-gray-700 bg-gray-800 py-2.5 pl-10 pr-3 text-sm text-gray-200 placeholder-gray-500 focus:border-accent focus:outline-none"
            />
          </div>
        </div>

        {/* Platforms */}
        <div>
          <label className="mb-2 block text-sm text-gray-400">Platforms</label>
          <div className="flex flex-wrap gap-2">
            {PLATFORMS.map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => togglePlatform(p)}
                className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                  form.platforms.includes(p)
                    ? "bg-accent text-white"
                    : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                }`}
              >
                {p}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-6">
          {/* Experience level */}
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-400">Experience</label>
            <select
              value={form.experience_level}
              onChange={(e) =>
                setForm((f) => ({ ...f, experience_level: e.target.value }))
              }
              className="rounded-lg border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm text-gray-200 focus:border-accent focus:outline-none"
            >
              <option value="entry">Entry</option>
              <option value="mid">Mid</option>
              <option value="senior">Senior</option>
              <option value="lead">Lead</option>
            </select>
          </div>

          {/* Remote toggle */}
          <label className="flex cursor-pointer items-center gap-2 text-sm text-gray-400">
            <input
              type="checkbox"
              checked={form.remote_only}
              onChange={(e) =>
                setForm((f) => ({ ...f, remote_only: e.target.checked }))
              }
              className="h-4 w-4 rounded border-gray-600 bg-gray-800 text-accent focus:ring-accent"
            />
            Remote Only
          </label>
        </div>

        <button
          type="submit"
          disabled={loading || !form.keywords.trim()}
          className="rounded-lg bg-accent px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-accent-hover disabled:opacity-50"
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <Loader2 size={16} className="animate-spin" /> Searching...
            </span>
          ) : (
            "Search Jobs"
          )}
        </button>
      </form>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 rounded-lg bg-red-500/10 px-4 py-3 text-sm text-red-400">
          <AlertCircle size={16} />
          {error}
        </div>
      )}

      {/* Results */}
      {loading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-accent" />
        </div>
      ) : results.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2">
          {results.map((job, i) => (
            <div
              key={`${job.url}-${i}`}
              className="rounded-xl border border-gray-800 bg-gray-900 p-5 transition-colors hover:border-gray-700"
            >
              <div className="mb-2 flex items-start justify-between">
                <div>
                  <h3 className="font-semibold text-gray-200">{job.title}</h3>
                  <p className="flex items-center gap-1 text-sm text-gray-400">
                    <Building2 size={14} /> {job.company}
                  </p>
                </div>
                <span className="rounded bg-gray-800 px-2 py-0.5 text-xs font-medium text-gray-300">
                  {job.platform}
                </span>
              </div>

              <div className="mb-3 flex flex-wrap gap-3 text-sm text-gray-400">
                {job.location && (
                  <span className="flex items-center gap-1">
                    <MapPin size={14} /> {job.location}
                  </span>
                )}
                {job.salary && <span className="text-emerald-400">{job.salary}</span>}
                {job.posted_date && (
                  <span className="text-gray-500">{job.posted_date}</span>
                )}
              </div>

              {job.description && (
                <p className="mb-3 line-clamp-3 text-sm text-gray-500">
                  {job.description}
                </p>
              )}

              <a
                href={job.url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-sm text-accent hover:underline"
              >
                View Job <ExternalLink size={14} />
              </a>
            </div>
          ))}
        </div>
      ) : searched && !loading ? (
        <p className="py-12 text-center text-gray-500">
          No results found. Try different keywords or filters.
        </p>
      ) : null}
    </div>
  );
}
