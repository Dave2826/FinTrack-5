import { useCallback, useEffect, useState } from 'react'
import { parseRoute, routeHref } from './routes'
import type { AppRoute } from './routes'

export function useHashRoute(): [AppRoute, (route: AppRoute) => void] {
  const [route, setRoute] = useState<AppRoute>(() =>
    parseRoute(window.location.hash),
  )

  useEffect(() => {
    function handleChange() {
      setRoute(parseRoute(window.location.hash))
    }

    window.addEventListener('hashchange', handleChange)
    return () => window.removeEventListener('hashchange', handleChange)
  }, [])

  const navigate = useCallback((next: AppRoute) => {
    if (window.location.hash !== routeHref(next)) {
      window.location.hash = routeHref(next)
    }
    setRoute(next)
  }, [])

  return [route, navigate]
}
