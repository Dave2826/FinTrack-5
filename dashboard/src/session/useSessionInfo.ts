import { useContext } from 'react'
import { SessionInfoContext } from './context'
import type { SessionInfoValue } from './context'

const FALLBACK: SessionInfoValue = {
  info: null,
  loading: false,
  error: null,
  companyId: null,
  can: () => false,
}

/** Sesión enriquecida; fuera del proveedor nunca concede permisos. */
export function useSessionInfo(): SessionInfoValue {
  return useContext(SessionInfoContext) ?? FALLBACK
}
