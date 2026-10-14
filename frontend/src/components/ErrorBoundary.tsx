import { Component, type ReactNode } from "react";
import { AlertTriangle, Home, RotateCcw } from "lucide-react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: string | null;
}

/**
 * ErrorBoundary catches React rendering errors and displays
 * a fallback UI with recovery options instead of crashing the app.
 */
export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error("React ErrorBoundary caught an error:", error, errorInfo);
    this.setState({
      errorInfo: errorInfo.componentStack ?? null,
    });
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  handleReload = () => {
    window.location.reload();
  };

  handleHome = () => {
    window.location.href = "/";
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-canvas p-4">
          <div className="w-full max-w-2xl">
            <div
              role="alert"
              className="rounded-2xl border border-fail/30 bg-surface p-8 shadow-xl"
            >
              <div className="flex items-start gap-4">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-fail/15 text-fail">
                  <AlertTriangle className="h-6 w-6" aria-hidden="true" />
                </div>
                <div className="min-w-0 flex-1">
                  <h1 className="text-xl font-bold text-ink">
                    Something went wrong
                  </h1>
                  <p className="mt-2 text-sm leading-6 text-muted">
                    The application encountered an unexpected error. This has
                    been logged for debugging. You can try reloading the page
                    or returning to the dashboard.
                  </p>

                  {this.state.error && (
                    <details className="mt-4">
                      <summary className="cursor-pointer text-sm font-semibold text-accent hover:underline">
                        Error details
                      </summary>
                      <div className="mt-3 space-y-2">
                        <div className="rounded-lg border border-line bg-sunken p-3">
                          <p className="text-xs font-semibold text-faint uppercase tracking-wide">
                            Error message
                          </p>
                          <p className="mt-1 font-mono text-xs text-fail">
                            {this.state.error.message}
                          </p>
                        </div>
                        {this.state.error.stack && (
                          <div className="rounded-lg border border-line bg-sunken p-3">
                            <p className="text-xs font-semibold text-faint uppercase tracking-wide">
                              Stack trace
                            </p>
                            <pre className="mt-1 overflow-x-auto font-mono text-[10px] leading-5 text-muted">
                              {this.state.error.stack}
                            </pre>
                          </div>
                        )}
                        {this.state.errorInfo && (
                          <div className="rounded-lg border border-line bg-sunken p-3">
                            <p className="text-xs font-semibold text-faint uppercase tracking-wide">
                              Component stack
                            </p>
                            <pre className="mt-1 overflow-x-auto font-mono text-[10px] leading-5 text-muted">
                              {this.state.errorInfo}
                            </pre>
                          </div>
                        )}
                      </div>
                    </details>
                  )}

                  <div className="mt-6 flex flex-wrap gap-3">
                    <button
                      onClick={this.handleReset}
                      className="btn btn-primary"
                    >
                      <RotateCcw className="h-4 w-4" aria-hidden="true" />
                      Try again
                    </button>
                    <button
                      onClick={this.handleReload}
                      className="btn btn-ghost"
                    >
                      Reload page
                    </button>
                    <button onClick={this.handleHome} className="btn btn-ghost">
                      <Home className="h-4 w-4" aria-hidden="true" />
                      Go home
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
