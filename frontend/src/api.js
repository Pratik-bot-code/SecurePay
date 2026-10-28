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

export function getCsrfToken() {
  return csrfToken;
}

function formatValidationError(errors) {
  if (Array.isArray(errors) && errors.length > 0) {
    const valErr = errors.find((e) => e.msg && typeof e.msg === "string");
    if (valErr) {
      return valErr.msg.replace(/^Value error,\s*/i, "").trim();
    }
    const error = errors.find((item) => Array.isArray(item.loc) && item.loc.includes("body"));
    if (error) {
      const field = error.loc.at(-1);
      if (field === "demo_handle" && error.type === "string_pattern_mismatch") {
        return "Profile ID must use only letters, numbers, periods, underscores, or hyphens.";
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
    }
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
      throw new ApiError("Cannot reach the backend server. Please verify that the SecurePay backend is running on http://127.0.0.1:8000.", 0);
    }
    throw error;
  }
  if (response.status === 204) return null;
  let data;
  try {
    data = await response.json();
  } catch {
    if (response.status >= 500) {
      throw new ApiError(`Cannot reach backend (HTTP ${response.status}). Please ensure the SecurePay backend is running on port 8000.`, response.status);
    }
    throw new ApiError("The server returned an invalid response.", response.status);
  }
  if (!response.ok) {
    const message = Array.isArray(data.detail)
      ? formatValidationError(data.detail)
      : typeof data.detail === "string"
        ? data.detail
        : response.status >= 500
          ? "The server could not complete this request."
          : "The request could not be completed. Check the information and try again.";
    throw new ApiError(message, response.status);
  }
  if (data?.csrf_token) setCsrfToken(data.csrf_token);
  return data;
}

export function toProfile(user) {
  return { name: user.display_name, handle: user.demo_handle, created_at: user.created_at };
}

// API client helper methods
export const api = {
  getDashboard: () => apiRequest("/dashboard"),

  // Transactions & Ledger
  getTransactions: (params = {}) => {
    const query = new URLSearchParams();
    if (params.search) query.set("search", params.search);
    if (params.direction && params.direction !== "all") query.set("direction", params.direction);
    if (params.period && params.period !== "all") query.set("period", params.period);
    if (params.status && params.status !== "all") query.set("status", params.status);
    if (params.sort) query.set("sort", params.sort);
    if (params.page) query.set("page", String(params.page));
    if (params.page_size) query.set("page_size", String(params.page_size));
    if (params.paginated) query.set("paginated", "true");
    const qs = query.toString();
    return apiRequest(`/transactions${qs ? `?${qs}` : ""}`);
  },

  getTransactionsSummary: () => apiRequest("/transactions/summary"),

  getTransaction: (ref) => apiRequest(`/transactions/${ref}`),

  getTransactionsExportUrl: (params = {}) => {
    const query = new URLSearchParams();
    if (params.search) query.set("search", params.search);
    if (params.direction && params.direction !== "all") query.set("direction", params.direction);
    if (params.period && params.period !== "all") query.set("period", params.period);
    const qs = query.toString();
    return `/api/transactions/export${qs ? `?${qs}` : ""}`;
  },

  // Bank Directory & Accounts
  getBankDirectory: (params = {}) => {
    const query = new URLSearchParams();
    if (params.search) query.set("search", params.search);
    if (params.category && params.category !== "all") query.set("category", params.category);
    if (params.popular_only) query.set("popular_only", "true");
    if (params.supported_only) query.set("supported_only", "true");
    const qs = query.toString();
    return apiRequest(`/banks/directory${qs ? `?${qs}` : ""}`);
  },

  lookupBankByIfsc: (ifsc) => apiRequest(`/banks/lookup/${ifsc}`),

  getLinkedBanks: () => apiRequest("/accounts/banks"),
  linkBank: (data) => apiRequest("/accounts/banks", { method: "POST", body: data }),
  unlinkBank: (bankId) => apiRequest(`/accounts/banks/${bankId}`, { method: "DELETE" }),
  setPrimaryBank: (bankId) => apiRequest(`/accounts/banks/${bankId}/primary`, { method: "POST" }),

  // Recipient Validation & Payment Orders
  validateRecipient: (data) => apiRequest("/payments/validate-recipient", { method: "POST", body: data }),
  createPaymentOrder: (data) => apiRequest("/payments/orders", { method: "POST", body: data }),
  getPaymentOrder: (orderRef) => apiRequest(`/payments/orders/${orderRef}`),
  getOrderHistory: (orderRef) => apiRequest(`/payments/orders/${orderRef}/history`),
  verifyPayment: (data) => apiRequest("/payments/verify", { method: "POST", body: data }),

  // Merchant Hub
  getMerchantProfile: () => apiRequest("/merchant"),
  registerMerchant: (data) => apiRequest("/merchant/register", { method: "POST", body: data }),

  // Notifications
  getNotifications: () => apiRequest("/notifications"),
  markNotificationRead: (id, read = true) => apiRequest(`/notifications/${id}`, { method: "PATCH", body: { read } }),
  markAllNotificationsRead: () => apiRequest("/notifications/read-all", { method: "POST" }),

  // Sessions & Security
  getSessions: () => apiRequest("/auth/sessions"),
  revokeSession: (id) => apiRequest(`/auth/sessions/${id}`, { method: "DELETE" }),
  changePassword: (data) => apiRequest("/auth/password", { method: "PUT", body: data }),
  updateProfile: (data) => apiRequest("/profile", { method: "PATCH", body: data }),
  updatePreferences: (data) => apiRequest("/preferences", { method: "PUT", body: data }),
  logout: () => apiRequest("/auth/logout", { method: "POST" }),
};
