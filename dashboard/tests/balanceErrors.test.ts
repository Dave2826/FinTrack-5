import { ApolloError } from '@apollo/client'
import { GraphQLError } from 'graphql'
import { describe, expect, it } from 'vitest'
import {
  BalanceError,
  classifyGraphQLErrors,
  toBalanceError,
} from '../src/lib/balanceErrors'

function graphQLError(message: string, code?: string): GraphQLError {
  return new GraphQLError(message, code ? { extensions: { code } } : {})
}

describe('classifyGraphQLErrors', () => {
  it('clasifica la ausencia de sesión', () => {
    expect(
      classifyGraphQLErrors([graphQLError('Usuario no autenticado')]),
    ).toBe('unauthenticated')
  })

  it('clasifica un token inválido o expirado', () => {
    expect(
      classifyGraphQLErrors([graphQLError('Token inválido o expirado')]),
    ).toBe('expired')
  })

  it('prioriza expirado sobre el código UNAUTHENTICATED', () => {
    expect(
      classifyGraphQLErrors([
        graphQLError('Token inválido o expirado', 'UNAUTHENTICATED'),
      ]),
    ).toBe('expired')
  })

  it('clasifica la falta de permisos', () => {
    expect(
      classifyGraphQLErrors([
        graphQLError('El rol no tiene el permiso transactions.read'),
      ]),
    ).toBe('forbidden')

    expect(
      classifyGraphQLErrors([
        graphQLError('La membresía no tiene un rol activo'),
      ]),
    ).toBe('forbidden')
  })

  it('clasifica los errores de fechas', () => {
    expect(
      classifyGraphQLErrors([
        graphQLError('fromDate no puede ser posterior a toDate'),
      ]),
    ).toBe('invalid-dates')

    expect(
      classifyGraphQLErrors([
        graphQLError(
          'Variable "$fromDate" has invalid value: Value cannot represent a Date: "2026-02-30". day is out of range for month',
        ),
      ]),
    ).toBe('invalid-dates')
  })

  it('no clasifica un error GraphQL genérico como autenticación', () => {
    expect(classifyGraphQLErrors([graphQLError('Algo inesperado')])).toBe(
      'graphql',
    )
  })
})

describe('toBalanceError', () => {
  it('clasifica un error de red', () => {
    const error = toBalanceError(
      new ApolloError({ networkError: new Error('fetch failed') }),
    )

    expect(error.kind).toBe('network')
    expect(error.message).toMatch(/conectar con el servidor/i)
    expect(error.technicalMessage).toBe('fetch failed')
  })

  it('clasifica errores GraphQL de autenticación y permisos', () => {
    expect(
      toBalanceError(
        new ApolloError({
          graphQLErrors: [graphQLError('Usuario no autenticado')],
        }),
      ).kind,
    ).toBe('unauthenticated')

    expect(
      toBalanceError(
        new ApolloError({
          graphQLErrors: [graphQLError('Token inválido o expirado')],
        }),
      ).kind,
    ).toBe('expired')

    expect(
      toBalanceError(
        new ApolloError({
          graphQLErrors: [
            graphQLError('El rol no tiene el permiso transactions.read'),
          ],
        }),
      ).kind,
    ).toBe('forbidden')
  })

  it('conserva el detalle técnico sin exponerlo en el mensaje público', () => {
    const error = toBalanceError(
      new ApolloError({
        graphQLErrors: [graphQLError('Usuario no autenticado')],
      }),
    )

    expect(error.message).not.toContain('Usuario no autenticado')
    expect(error.technicalMessage).toContain('Usuario no autenticado')
  })

  it('devuelve la misma instancia si ya es un BalanceError', () => {
    const original = new BalanceError('graphql', 'mensaje', 'detalle')

    expect(toBalanceError(original)).toBe(original)
  })

  it('clasifica un error desconocido como GraphQL general', () => {
    expect(toBalanceError('algo raro').kind).toBe('graphql')
    expect(toBalanceError(new Error('boom')).kind).toBe('graphql')
  })
})
