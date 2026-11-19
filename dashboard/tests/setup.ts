import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, beforeEach } from 'vitest'
import { tokenStore } from '../src/auth/tokenStore'

beforeEach(() => {
  // El token vive en memoria; se reinicia entre pruebas.
  tokenStore.clear()
  localStorage.clear()
  sessionStorage.clear()
  // La navegación vive en el hash; cada prueba empieza en el dashboard
  // financiero.
  window.history.replaceState(null, '', '/')
})

afterEach(() => {
  cleanup()
})
