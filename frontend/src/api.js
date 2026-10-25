let csrfToken = "";

export class ApiError extends Error {
  constructor(message, statusCode) {
    super(message);
    this.name = "ApiError";
    this.statusCode = statusCode;
  }
}

export function setCsrfToken(value) {
  csrfToken = value || "";
}

function formatValidationError(errors) {
  const error = errors.find((item) => Array.isArray(item.loc) && item.loc.includes("body"));
  if (!error) return "Check the information entered and try again.";

  const field = error.loc.at(-1);
  if (field === "demo_handle" && error.type === "string_pattern_mismatch") {
    return "Profile ID must use only letters, numbers, periods, underscores, or hyphens. Email addresses are not supported.";
  }
  if (field === "demo_handle" && error.type === "string_too_short") {
    return "Profile ID must contain at least 3 characters.";
  }
  if (field === "password" && error.type === "string_too_short") {
    return "Password must contain at least 12 characters.";
  }
  if (field === "display_name" && error.type === "string_too_short") {
    return "Enter your display name.";
  }
  return "Some account details are invalid. Check the fields and try again.";
}

export async function apiRequest(path, { method = "GET", body, headers = {} } = {}) {
  const requestHeaders = new Headers(headers);
  if (body !== undefined) requestHeaders.set("Content-Type", "application/json");
  if (!["GET", "HEAD", "OPTIONS"].includes(method.toUpperCase()) && csrfToken) {
    requestHeaders.set("X-CSRF-Token", csrfToken);
  }
  let response;
  try {
    response = await fetch(`/api${path}`, {
      method,
      credentials: "include",
      headers: requestHeaders,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (error) {
    if (error instanceof TypeError) {
      throw new ApiError("Cannot reach the backend. Start FastAPI and check http://127.0.0.1:8000/api/health.", 0);
    }
    throw error;
  }
  if (response.status === 204) return null;
  let data;
  try {
    data = await response.json();
  } catch {
    if (response.status >= 500) {
      throw new ApiError("Cannot reach the backend. Start FastAPI and check http://127.0.0.1:8000/api/health.", response.status);
    }
    throw new ApiError("The server returned an invalid response.", response.status);
  }
  if (!response.ok) {
    const message = Array.isArray(data.detail)
      ? formatValidationError(data.detail)
      : typeof data.detail === "string"
        ? data.detail.replace(/\bdemo\b/gi, "simulated")
        : response.status >= 500
          ? "The server could not complete this request. Check the backend terminal for details."
          : "The request could not be completed. Check the information and try again.";
    throw new ApiError(message, response.status);
  }
  if (data?.csrf_token) setCsrfToken(data.csrf_token);
  return data;
}

export function toProfile(user) {
  return { name: user.display_name, handle: user.demo_handle };
}
