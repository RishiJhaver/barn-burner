/**
 * JWT Token validation and decoding utilities.
 */

export interface DecodedToken {
  sub?: string;
  email?: string;
  username?: string;
  exp?: number;
  iat?: number;
  'custom:role'?: string;
  role?: string;
  [key: string]: any;
}

/**
 * Safely decodes base64url encoded JWT payload.
 */
export function parseJwt(token: string): DecodedToken | null {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    const base64Url = parts[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(jsonPayload);
  } catch {
    return null;
  }
}

/**
 * Checks whether a JWT token is expired based on its 'exp' timestamp.
 * Returns true if expired or malformed, false if still valid.
 */
export function isTokenExpired(token: string | null): boolean {
  if (!token) return true;
  const payload = parseJwt(token);
  if (!payload || !payload.exp) return true;

  // payload.exp is in seconds since epoch; Date.now() is in ms.
  // We add a 5-second buffer to guard against minor clock drift.
  const expirationMs = payload.exp * 1000;
  return expirationMs <= Date.now() + 5000;
}
