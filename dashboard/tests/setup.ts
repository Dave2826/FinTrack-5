import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, beforeEach } from 'vitest'
import { tokenStore } from '../src/auth/tokenStore'

beforeEach(() => {
  // El token vive en memoria; se reinicia entre pruebas.
  tokenStore.clear()
  localStorage.clear()
  sessionStorage.clear()
})

afterEach(() => {
  cleanup()
})
