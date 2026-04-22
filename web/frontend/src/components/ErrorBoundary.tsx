import { Component, type ErrorInfo, type ReactNode } from "react";
import { AlertTriangle } from "lucide-react";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
  info: ErrorInfo | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null, info: null };

  static getDerivedStateFromError(error: Error): State {
    return { error, info: null };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("[JobPilot UI] Uncaught error:", error, info);
    this.setState({ error, info });
  }

  reset = () => this.setState({ error: null, info: null });

  render() {
    if (!this.state.error) return this.props.children;

    return (
      <div className="flex h-screen items-center justify-center bg-gray-950 p-6 text-gray-100">
        <div className="max-w-2xl rounded-xl border border-red-500/30 bg-red-500/5 p-6">
          <div className="mb-3 flex items-center gap-2 text-red-400">
            <AlertTriangle size={20} />
            <h1 className="text-lg font-semibold">Something went wrong</h1>
          </div>
          <p className="mb-4 text-sm text-gray-300">
            A page crashed while rendering. The error and component stack are
            logged to the browser console.
          </p>
          <pre className="mb-4 max-h-64 overflow-auto rounded-lg bg-gray-900 p-3 text-xs text-red-300">
            {this.state.error.message}
            {this.state.info?.componentStack}
          </pre>
          <button
            onClick={this.reset}
            className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white hover:opacity-90"
          >
            Try again
          </button>
        </div>
      </div>
    );
  }
}
