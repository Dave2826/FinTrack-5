import { MockedProvider } from '@apollo/client/testing'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import App from '../src/App'

describe('App', () => {
  it('muestra la identidad de FinTrack-5 y el formulario de acceso', () => {
    render(
      <MockedProvider mocks={[]} addTypename={false}>
        <App />
      </MockedProvider>,
    )

    expect(
      screen.getByRole('heading', { level: 1, name: 'FinTrack-5' }),
    ).toBeInTheDocument()
    expect(screen.getByText('Panel financiero')).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { level: 2, name: 'Inicia sesión' }),
    ).toBeInTheDocument()
    expect(screen.getByLabelText('Correo electrónico')).toBeInTheDocument()
    expect(screen.getByLabelText('Contraseña')).toBeInTheDocument()
  })
})
