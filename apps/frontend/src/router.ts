import {
  createRouter,
  type RouteLocationNormalized,
  type RouteLocationResolved,
  type RouteRecordRaw,
  type Router,
  type RouterHistory,
} from 'vue-router'
import type { ApiServices } from './features/api/contracts'
import ApiAuth from './features/ApiAuth.vue'
import ShipmentView from './features/ShipmentView.vue'
import UserRoles from './features/UserRoles.vue'
import AccountSettings from './screens/AccountSettings.vue'
import DevicesScreen from './screens/DevicesScreen.vue'
import DeviceSetupScreen from './screens/DeviceSetupScreen.vue'
import type { DeviceCategory } from './types/device-ui'

declare module 'vue-router' {
  interface RouteMeta {
    requiresAdmin?: boolean
    guide?: DeviceCategory
  }
}

const routes: RouteRecordRaw[] = [
  { path: '/login', name: 'login', component: ApiAuth },
  { path: '/shipments', name: 'shipments', component: ShipmentView },
  {
    path: '/shipments/:id',
    name: 'shipment-detail',
    component: ShipmentView,
  },
  {
    path: '/devices',
    name: 'devices',
    component: DevicesScreen,
    meta: { requiresAdmin: true },
  },
  {
    path: '/devices/setup/esp32',
    name: 'esp32-setup',
    component: DeviceSetupScreen,
    meta: { requiresAdmin: true, guide: 'esp32' },
  },
  {
    path: '/devices/setup/cameras',
    name: 'bardi-setup',
    component: DeviceSetupScreen,
    meta: { requiresAdmin: true, guide: 'bardi' },
  },
  {
    path: '/members',
    name: 'members',
    component: UserRoles,
    meta: { requiresAdmin: true },
  },
  { path: '/settings', name: 'settings', component: AccountSettings },
  {
    path: '/deliveries/:id?',
    redirect: (to) => ({
      path: to.path.replace('/deliveries', '/shipments'),
      query: to.query,
      hash: to.hash,
    }),
  },
  { path: '/:pathMatch(.*)*', redirect: '/shipments' },
]

// oxlint-disable-next-line no-control-regex -- Reject control characters in shipment identifiers.
const unsafeShipmentId = /[\s/\\?#\u0000-\u001f]/

function hasValidShipmentId(path: string) {
  const encodedId = path.slice('/shipments/'.length)
  if (!encodedId || encodedId.length > 200) return false
  try {
    return !unsafeShipmentId.test(decodeURIComponent(encodedId))
  } catch {
    return false
  }
}

function canResume(
  route: Pick<RouteLocationResolved, 'name' | 'meta' | 'path'>,
) {
  return (
    route.meta.guide !== undefined ||
    (route.name === 'shipment-detail' && hasValidShipmentId(route.path))
  )
}

export function loginRoute(from: RouteLocationNormalized) {
  return {
    name: 'login',
    query: canResume(from) ? { redirect: from.fullPath } : {},
  }
}

export function signedInRoute(router: Router, redirect: unknown) {
  if (
    typeof redirect === 'string' &&
    redirect.startsWith('/') &&
    !redirect.startsWith('//')
  ) {
    const target = router.resolve(redirect)
    if (canResume(target))
      return { path: target.path, query: target.query, hash: target.hash }
  }
  return { name: 'shipments' }
}

export function createAppRouter(
  services: Pick<ApiServices, 'user'>,
  history: RouterHistory,
) {
  const router = createRouter({
    history,
    routes,
    strict: true,
    sensitive: true,
    scrollBehavior: () => ({ top: 0, left: 0 }),
  })

  router.beforeEach((to) => {
    if (to.name === 'shipment-detail' && !hasValidShipmentId(to.path))
      return { name: 'shipments', replace: true }

    const user = services.user()
    if (!user && to.name !== 'login')
      return { ...loginRoute(to), replace: true }
    if (to.name === 'login' && user) {
      return { ...signedInRoute(router, to.query.redirect), replace: true }
    }
    if (to.meta.requiresAdmin && user?.role !== 'admin')
      return { name: 'shipments', replace: true }
  })

  return router
}
