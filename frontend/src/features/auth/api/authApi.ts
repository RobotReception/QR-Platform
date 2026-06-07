import http, { STORAGE } from '@services/http/client'
import type {
  AuthResponse, LoginRequest, SignupRequest,
  SendOtpRequest, VerifyOtpRequest, ConfirmNewPasswordRequest, OtpResponse,
  MeResponse,
} from '../types'

export const authAPI = {
  // POST /auth/login
  login: async (body: LoginRequest): Promise<AuthResponse> => {
    const { data } = await http.post<AuthResponse>('/auth/login', body)

    if (data.access_token)  localStorage.setItem(STORAGE.ACCESS_TOKEN,  data.access_token)
    if (data.refresh_token) localStorage.setItem(STORAGE.REFRESH_TOKEN, data.refresh_token)
    if (data.tenants?.[0])  localStorage.setItem(STORAGE.TENANT_ID, data.tenants[0].tenant_id)

    return data
  },

  // POST /auth/signup
  signup: async (body: SignupRequest): Promise<AuthResponse> => {
    const { data } = await http.post<AuthResponse>('/auth/signup', body)
    return data
  },

  // POST /auth/logout
  logout: async (): Promise<void> => {
    try { await http.post('/auth/logout') } finally {
      Object.values(STORAGE).forEach(k => localStorage.removeItem(k))
    }
  },

  // GET /auth/me
  me: async (): Promise<MeResponse> => {
    const { data } = await http.get<MeResponse>('/auth/me')
    return data
  },

  // ── OTP Password Reset (3 steps) ──

  // POST /auth/password-reset/send-otp
  sendOtp: async (body: SendOtpRequest): Promise<OtpResponse> => {
    const { data } = await http.post<OtpResponse>('/auth/password-reset/send-otp', body)
    return data
  },

  // POST /auth/password-reset/verify-otp
  verifyOtp: async (body: VerifyOtpRequest): Promise<OtpResponse> => {
    const { data } = await http.post<OtpResponse>('/auth/password-reset/verify-otp', body)
    return data
  },

  // POST /auth/password-reset/confirm-new
  confirmNewPassword: async (body: ConfirmNewPasswordRequest): Promise<OtpResponse> => {
    const { data } = await http.post<OtpResponse>('/auth/password-reset/confirm-new', body)
    return data
  },

  // POST /auth/refresh
  refresh: async (refresh_token: string): Promise<AuthResponse> => {
    const { data } = await http.post<AuthResponse>('/auth/refresh', { refresh_token })
    return data
  },
}
