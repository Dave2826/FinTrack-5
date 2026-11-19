import { createContext } from 'react'
import type { SessionInfo } from '../types/admin'

export interface SessionInfoValue {
  /** Datos de `me`, o `null` mientras carga o si no se pudieron leer. */
  info: SessionInfo | null
  loading: boolean
  /** Mensaje si `me` falló por un motivo distinto a la sesión. */
  error: string | null
  /** Empresa de la sesión: de `me` o, mientras carga, del token. */
  companyId: number | null
  /** ¿El rol de la sesión tiene el permiso? `false` mientras carga. */
  can: (permission: string) => boolean
}

export const SessionInfoContext = createContext<SessionInfoValue | null>(null)
