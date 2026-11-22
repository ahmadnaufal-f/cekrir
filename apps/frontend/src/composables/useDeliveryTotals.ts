import { onMounted, onUnmounted, shallowRef, watch } from 'vue'
import { getCalendarDate } from '../lib/delivery-date'
import { deliveryRequestStatus } from '../lib/delivery-copy'
import type { DeliveryService } from '../services/contracts'
import type { DeliveryTotals, DeliveryTotalsQuery } from '../types/app'

function localQuery(): DeliveryTotalsQuery {
  const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone
  return { date: getCalendarDate(new Date(), timeZone), timeZone }
}

export function useDeliveryTotals(options: {
  service: () => DeliveryService
  userKey: () => string
  refreshKey: () => number
  onSessionExpired: () => void
}) {
  const query = shallowRef(localQuery())
  const totals = shallowRef<DeliveryTotals | null>(null)
  const pending = shallowRef(true)
  const failed = shallowRef(false)
  let version = 0
  let disposed = false
  let mounted = false
  let midnight: ReturnType<typeof setTimeout> | undefined

  function scheduleNextDay() {
    if (!mounted || disposed) return
    clearTimeout(midnight)
    const now = new Date()
    // Local calendar arithmetic follows daylight-saving changes as well.
    const tomorrow = new Date(
      now.getFullYear(),
      now.getMonth(),
      now.getDate() + 1,
    )
    midnight = setTimeout(
      () => void reload(),
      tomorrow.getTime() - now.getTime() + 50,
    )
  }

  async function reload(clear = false): Promise<void> {
    const request = ++version
    const requested = localQuery()
    if (
      clear ||
      requested.date !== query.value.date ||
      requested.timeZone !== query.value.timeZone
    )
      totals.value = null
    query.value = requested
    pending.value = true
    failed.value = false
    scheduleNextDay()
    try {
      const result = await options.service().totals(requested)
      if (disposed || request !== version) return
      if (
        !result ||
        result.date !== requested.date ||
        result.timeZone !== requested.timeZone ||
        !Number.isSafeInteger(result.receivedToday) ||
        result.receivedToday < 0 ||
        !Number.isSafeInteger(result.receivedAllTime) ||
        result.receivedAllTime < result.receivedToday
      )
        throw new Error('Invalid delivery totals')
      totals.value = result
    } catch (cause) {
      if (disposed || request !== version) return
      totals.value = null
      failed.value = true
      if (deliveryRequestStatus(cause) === 401) options.onSessionExpired()
    } finally {
      if (!disposed && request === version) pending.value = false
    }
  }

  watch(
    () => [options.service(), options.userKey(), options.refreshKey()] as const,
    () => void reload(true),
    { immediate: true },
  )
  onMounted(() => {
    mounted = true
    scheduleNextDay()
  })
  onUnmounted(() => {
    disposed = true
    version++
    clearTimeout(midnight)
  })
  return { query, totals, pending, failed, reload }
}
