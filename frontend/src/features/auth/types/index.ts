export interface TenantInfo {
  tenant_id:        string
  slug:             string
  name:             string
  tenant_status:    string
  plan:             string
  role:             string
  membership_status:string
}

export interface AuthResponse {
  message:                  string
  user_id?:                 string
  access_token?:            string
  refresh_token?:           string
  tenants?:                 TenantInfo[]
  requires_tenant_selection?:boolean
}

export interface AuthUser {
  id:        string
  email:     string
  full_name: string | null
  avatar_url:string | null
  is_staff:  boolean
}

export interface MeResponse extends AuthUser {
  user_id?:    string
  tenants?:    TenantInfo[]
  permissions?: string[]
}

export interface AuthState {
  user:    AuthUser | null
  tenants: TenantInfo[]
  currentTenantId: string | null
}

// ── Requests ──
export interface LoginRequest {
  email:      string
  password:   string
  tenant_id?: string
}

export interface SignupRequest {
  email:              string
  password:           string
  full_name?:         string
  organization_name?: string
}

export interface ForgotPasswordRequest {
  email: string
}

// ── OTP Password Reset ──
export interface SendOtpRequest {
  email: string
}

export interface VerifyOtpRequest {
  email:    string
  otp_code: string
}

export interface ConfirmNewPasswordRequest {
  reset_token:  string
  new_password: string
}

export interface OtpResponse {
  message:             string
  email?:              string
  reset_token?:        string
  remaining_attempts?: number
  blocked_until?:      string
}
