import { MockedProvider } from '@apollo/client/testing'
import type { MockedResponse } from '@apollo/client/testing'
import { render } from '@testing-library/react'
import App from '../../src/App'

export function renderApp(mocks: readonly MockedResponse[] = []) {
  return render(
    <MockedProvider mocks={[...mocks]} addTypename={false}>
      <App />
    </MockedProvider>,
  )
}
