import { Component, type ErrorInfo, type ReactNode } from "react";

interface ErrorBoundaryFallbackProps {
  reset: () => void;
}

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  fallbackRender?: (props: ErrorBoundaryFallbackProps) => ReactNode;
  onError?: (error: Error, info: ErrorInfo) => void;
  onReset?: () => void;
  resetKeys?: unknown[];
}

interface ErrorBoundaryState {
  hasError: boolean;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  public state: ErrorBoundaryState = {
    hasError: false
  };

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    if (import.meta.env.DEV) {
      console.error("ErrorBoundary caught a rendering error.", error, info);
    }

    try {
      this.props.onError?.(error, info);
    } catch {
      // Never let error reporting fail the fallback path.
    }
  }

  private handleReset = () => {
    this.setState({ hasError: false });
    this.props.onReset?.();
  };

  render() {
    if (!this.state.hasError) {
      return this.props.children;
    }

    if (this.props.fallbackRender) {
      return this.props.fallbackRender({ reset: this.handleReset });
    }

    if (this.props.fallback) {
      return this.props.fallback;
    }

    return (
      <section className="mx-auto mt-8 w-full max-w-sm rounded-2xl border border-border bg-muted/50 p-5" role="alert" aria-live="assertive">
        <h2 className="text-base font-semibold text-foreground">Something went wrong</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          The app hit an unexpected issue. Please try again and continue your onboarding.
        </p>
        <button
          type="button"
          onClick={this.handleReset}
          className="mt-4 min-h-10 rounded-full border border-border bg-background px-4 text-sm font-medium text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
        >
          Try again
        </button>
      </section>
    );
  }
}
