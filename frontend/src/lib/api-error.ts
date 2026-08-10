/**
 * API Error Formatting Utilities
 *
 * Provides consistent error message formatting for API responses
 * used in dialog components (EditAgentDialog, AgentDialog, etc.).
 */

/**
 * Format an API error into a user-friendly alert message.
 * Handles various error shapes: string, Error, Axios-style, fetch-style.
 */
export function formatApiErrorForAlert(error: unknown): string {
  if (!error) return "Unknown error occurred";

  // String error
  if (typeof error === "string") return error;

  // Error instance
  if (error instanceof Error) return error.message;

  // Axios-style error response
  if (typeof error === "object" && error !== null) {
    const err = error as Record<string, any>;

    // FastAPI/Starlette validation error
    if (err.detail) {
      if (typeof err.detail === "string") return err.detail;
      if (Array.isArray(err.detail)) {
        return err.detail
          .map((d: any) => d.msg || JSON.stringify(d))
          .join("; ");
      }
      return String(err.detail);
    }

    // Generic message field
    if (typeof err.message === "string") return err.message;

    // Response with status text
    if (err.statusText && err.status) {
      return `[${err.status}] ${err.statusText}`;
    }
  }

  return "An unexpected error occurred";
}