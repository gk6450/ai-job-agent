import { useEffect, useState } from "react";
import {
  Download,
  FileText,
  Loader2,
  AlertCircle,
  Sparkles,
  File,
} from "lucide-react";
import {
  getGeneratedDocs,
  downloadDoc,
  tailorResume,
  type GeneratedDoc,
  type TailorRequest,
} from "@/lib/api";

export default function ResumeReview() {
  const [docs, setDocs] = useState<GeneratedDoc[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [tailorForm, setTailorForm] = useState<TailorRequest>({
    job_description: "",
    job_title: "",
    company: "",
  });
  const [tailoring, setTailoring] = useState(false);
  const [tailorResult, setTailorResult] = useState("");

  useEffect(() => {
    getGeneratedDocs()
      .then((r) => setDocs(r.data))
      .catch((e) => setError(e.message ?? "Failed to load documents"))
      .finally(() => setLoading(false));
  }, []);

  const handleTailor = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tailorForm.job_description || !tailorForm.job_title) return;
    setTailoring(true);
    setTailorResult("");
    try {
      await tailorResume(tailorForm);
      setTailorResult("Resume tailored successfully! Refreshing documents...");
      const r = await getGeneratedDocs();
      setDocs(r.data);
    } catch {
      setTailorResult("Failed to tailor resume. Please try again.");
    } finally {
      setTailoring(false);
    }
  };

  const docIcon = (type: string) =>
    type === "resume" ? (
      <FileText className="h-5 w-5 text-blue-400" />
    ) : (
      <File className="h-5 w-5 text-violet-400" />
    );

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
      {/* Tailor form */}
      <div className="rounded-xl border border-gray-800 bg-gray-900 p-6">
        <div className="mb-5 flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-accent" />
          <h2 className="text-sm font-semibold text-gray-200">
            Tailor Resume for a Job
          </h2>
        </div>

        <form onSubmit={handleTailor} className="space-y-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-gray-500">
                Job Title
              </label>
              <input
                type="text"
                value={tailorForm.job_title}
                onChange={(e) =>
                  setTailorForm({ ...tailorForm, job_title: e.target.value })
                }
                placeholder="e.g. Senior React Developer"
                className="w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-200 outline-none focus:border-accent"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-gray-500">
                Company
              </label>
              <input
                type="text"
                value={tailorForm.company}
                onChange={(e) =>
                  setTailorForm({ ...tailorForm, company: e.target.value })
                }
                placeholder="e.g. Google"
                className="w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-200 outline-none focus:border-accent"
              />
            </div>
          </div>

          <div>
            <label className="mb-1.5 block text-xs font-medium text-gray-500">
              Job Description
            </label>
            <textarea
              value={tailorForm.job_description}
              onChange={(e) =>
                setTailorForm({
                  ...tailorForm,
                  job_description: e.target.value,
                })
              }
              rows={6}
              placeholder="Paste the full job description here..."
              className="w-full resize-none rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-200 outline-none focus:border-accent"
            />
          </div>

          <div className="flex items-center gap-4">
            <button
              type="submit"
              disabled={
                tailoring || !tailorForm.job_description || !tailorForm.job_title
              }
              className="flex items-center gap-2 rounded-lg bg-accent px-5 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-hover disabled:opacity-50"
            >
              {tailoring ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Sparkles className="h-4 w-4" />
              )}
              Tailor Resume
            </button>
            {tailorResult && (
              <p
                className={`text-sm ${
                  tailorResult.includes("success")
                    ? "text-emerald-400"
                    : "text-red-400"
                }`}
              >
                {tailorResult}
              </p>
            )}
          </div>
        </form>
      </div>

      {/* Generated documents */}
      <div className="rounded-xl border border-gray-800 bg-gray-900 p-6">
        <h2 className="mb-5 text-sm font-semibold text-gray-200">
          Generated Documents
        </h2>

        {docs.length === 0 ? (
          <div className="flex h-48 flex-col items-center justify-center gap-2 text-gray-500">
            <FileText className="h-10 w-10" />
            <p className="text-sm">No documents generated yet</p>
          </div>
        ) : (
          <div className="grid gap-3">
            {docs.map((doc, i) => (
              <div
                key={i}
                className="flex items-center justify-between rounded-lg border border-gray-800 bg-gray-850 px-4 py-3"
              >
                <div className="flex items-center gap-3">
                  {docIcon(doc.doc_type)}
                  <div>
                    <p className="text-sm font-medium text-gray-200">
                      {doc.filename}
                    </p>
                    <p className="text-xs text-gray-500">
                      {doc.company} · {doc.role} ·{" "}
                      {new Date(doc.created_at).toLocaleDateString()}
                    </p>
                  </div>
                </div>
                <a
                  href={downloadDoc(doc.doc_type, doc.filename)}
                  className="flex items-center gap-1.5 rounded-lg border border-gray-700 bg-gray-800 px-3 py-1.5 text-xs font-medium text-gray-300 transition-colors hover:bg-gray-700 hover:text-white"
                >
                  <Download className="h-3.5 w-3.5" />
                  Download
                </a>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
