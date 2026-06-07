import type { ReactNode } from 'react'
import { usePermission, useAnyPermission } from './usePermission'
import type { PermissionKey } from './keys'

interface CanProps {
  permission?: PermissionKey | string
  anyOf?: (PermissionKey | string)[]
  children: ReactNode
  fallback?: ReactNode
}

/** Renders children only when the user has the required permission(s). */
export function Can({ permission, anyOf, children, fallback = null }: CanProps) {
  const hasSingle = permission ? usePermission(permission) : true
  const hasAny = anyOf ? useAnyPermission(...anyOf) : true

  if (!hasSingle || !hasAny) return <>{fallback}</>
  return <>{children}</>
}
