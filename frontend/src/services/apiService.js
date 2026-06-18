// In development: Vite proxies /api -> http://127.0.0.1:8000 (see vite.config.js)
// In production: set VITE_API_URL env var or deploy behind the same origin
const API_URL = import.meta.env.VITE_API_URL ?? '/api';

export async function fetchHighRiskAccounts() {
  try {
    const response = await fetch(`${API_URL}/accounts/high-risk`);
    if (!response.ok) {
      throw new Error(`API returned connection error status: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error("High-risk accounts fetch failure:", error);
    throw error;
  }
}

export async function fetchAccountFeatures(accountId) {
  try {
    const response = await fetch(`${API_URL}/accounts/${accountId}/features`);
    if (!response.ok) {
      throw new Error(`API error fetching features: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error(`Features fetch failure for ${accountId}:`, error);
    throw error;
  }
}

export async function fetchAccountShap(accountId) {
  try {
    const response = await fetch(`${API_URL}/accounts/${accountId}/shap`);
    if (!response.ok) {
      throw new Error(`API error fetching SHAP: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error(`SHAP fetch failure for ${accountId}:`, error);
    throw error;
  }
}

export async function fetchAccountClaims(accountId) {
  try {
    const response = await fetch(`${API_URL}/accounts/${accountId}/claims`);
    if (!response.ok) {
      throw new Error(`API error fetching claims: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error(`Claims fetch failure for ${accountId}:`, error);
    throw error;
  }
}

export async function fetchAccountTransactions(accountId) {
  try {
    const response = await fetch(`${API_URL}/accounts/${accountId}/transactions`);
    if (!response.ok) {
      throw new Error(`API error fetching transactions: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error(`Transactions fetch failure for ${accountId}:`, error);
    throw error;
  }
}

export async function fetchAccountCopilot(accountId) {
  try {
    const response = await fetch(`${API_URL}/accounts/${accountId}/copilot`);
    if (!response.ok) {
      throw new Error(`API error fetching copilot SAR: ${response.status}`);
    }
    const data = await response.json();
    return data.report;
  } catch (error) {
    console.error(`Copilot fetch failure for ${accountId}:`, error);
    throw error;
  }
}

export async function fetchTypologyAlerts() {
  try {
    const response = await fetch(`${API_URL}/typology-alerts`);
    if (!response.ok) {
      throw new Error(`API error fetching typology alerts: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error("Typology alerts fetch failure:", error);
    throw error;
  }
}
export async function fetchHealthStatus() {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 3000);
    const response = await fetch(`${API_URL}/health`, { signal: controller.signal });
    clearTimeout(timeout);
    if (!response.ok) return { status: 'degraded', version: '?' };
    return await response.json();
  } catch {
    return { status: 'offline', version: '?' };
  }
}
