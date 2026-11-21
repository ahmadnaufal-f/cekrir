import { onScopeDispose, readonly, shallowRef, watch } from 'vue'
import type { Ref } from 'vue'

const DIRECTION_LOCK_PX = 8
const MAX_DISTANCE_PX = 96
const REFRESH_DISTANCE_PX = 64
const REFRESH_HOLD_PX = 48
const CLICK_SUPPRESSION_MS = 800

interface PullGesture {
  startX: number
  startY: number
  locked: boolean
  claimed: boolean
}

interface PullToRefreshOptions {
  disabled: () => boolean
  onRefresh: () => Promise<void>
}

/**
 * Adds touch-only pull-to-refresh handling to a page's existing list container.
 * The element keeps its normal viewport scrolling; only a downward gesture that
 * starts at the top can claim touch movement.
 */
export function usePullToRefresh(
  target: Readonly<Ref<HTMLElement | null>>,
  options: PullToRefreshOptions,
) {
  const distance = shallowRef(0)
  const armed = shallowRef(false)
  const refreshing = shallowRef(false)

  let currentTarget: HTMLElement | null = null
  let gesture: PullGesture | null = null
  let suppressClickUntil = 0
  let lifecycleVersion = 0
  let disposed = false

  function resetPull() {
    distance.value = 0
    armed.value = false
  }

  function cancelGesture() {
    gesture = null
    if (!refreshing.value) resetPull()
  }

  function scrollPositionsAreAtTop(element: HTMLElement): boolean {
    if (window.scrollY > 0) return false

    for (
      let ancestor: HTMLElement | null = element;
      ancestor;
      ancestor = ancestor.parentElement
    ) {
      if (ancestor.scrollTop > 0) return false
    }

    const scrollingElement = document.scrollingElement
    if (scrollingElement && scrollingElement.scrollTop > 0) return false

    return true
  }

  function beginsInInteractiveControl(
    event: TouchEvent,
    container: HTMLElement,
  ): boolean {
    for (const node of event.composedPath()) {
      if (node instanceof Element) {
        if (node.matches('button, input, select, textarea')) return true
        if ((node as HTMLElement).isContentEditable) return true
      }

      if (node === container) break
    }

    return false
  }

  function suppressFollowingClick() {
    suppressClickUntil = Date.now() + CLICK_SUPPRESSION_MS
  }

  function onTouchStart(event: TouchEvent) {
    // A new touch sequence always makes the next deliberate tap eligible again.
    suppressClickUntil = 0

    if (event.touches.length !== 1) {
      if (gesture?.claimed) suppressFollowingClick()
      cancelGesture()
      return
    }

    const element = currentTarget
    const touch = event.touches[0]
    if (
      !element ||
      !event.composedPath().includes(element) ||
      options.disabled() ||
      refreshing.value ||
      !touch
    ) {
      cancelGesture()
      return
    }

    if (
      !scrollPositionsAreAtTop(element) ||
      beginsInInteractiveControl(event, element)
    ) {
      cancelGesture()
      return
    }

    gesture = {
      startX: touch.clientX,
      startY: touch.clientY,
      locked: false,
      claimed: false,
    }
    resetPull()
  }

  function onTouchMove(event: TouchEvent) {
    const activeGesture = gesture
    if (!activeGesture) return

    if (event.touches.length !== 1) {
      if (activeGesture.claimed) suppressFollowingClick()
      cancelGesture()
      return
    }

    const touch = event.touches[0]
    if (!touch) return

    const deltaX = touch.clientX - activeGesture.startX
    const deltaY = touch.clientY - activeGesture.startY

    if (!activeGesture.locked) {
      if (Math.max(Math.abs(deltaX), Math.abs(deltaY)) < DIRECTION_LOCK_PX)
        return

      if (deltaY <= 0 || Math.abs(deltaX) >= deltaY) {
        cancelGesture()
        return
      }

      if (!event.cancelable) {
        cancelGesture()
        return
      }

      activeGesture.locked = true
      activeGesture.claimed = true
    }

    if (!event.cancelable) {
      if (activeGesture.claimed) suppressFollowingClick()
      cancelGesture()
      return
    }

    event.preventDefault()

    distance.value = Math.min(MAX_DISTANCE_PX, Math.max(0, deltaY) * 0.5)
    armed.value = distance.value >= REFRESH_DISTANCE_PX
  }

  function startRefresh() {
    if (refreshing.value || options.disabled()) {
      resetPull()
      return
    }

    const requestVersion = lifecycleVersion
    refreshing.value = true
    distance.value = REFRESH_HOLD_PX
    armed.value = true

    void (async () => {
      try {
        await options.onRefresh()
      } catch {
        // The caller owns error presentation. The gesture controller only owns
        // its temporary loading state.
      } finally {
        if (!disposed && requestVersion === lifecycleVersion) {
          refreshing.value = false
          resetPull()
        }
      }
    })()
  }

  function onTouchEnd(event: TouchEvent) {
    const activeGesture = gesture
    if (!activeGesture) return

    gesture = null
    if (activeGesture.claimed) suppressFollowingClick()

    if (event.touches.length === 0 && activeGesture.claimed && armed.value) {
      startRefresh()
    } else {
      resetPull()
    }
  }

  function onTouchCancel() {
    if (gesture?.claimed) suppressFollowingClick()
    cancelGesture()
  }

  function onClickCapture(event: MouseEvent) {
    if (Date.now() > suppressClickUntil || event.detail === 0) return
    const source = (
      event as MouseEvent & {
        sourceCapabilities?: { firesTouchEvents: boolean } | null
      }
    ).sourceCapabilities
    // A real mouse click on a hybrid device is a new intentional action.
    if (source?.firesTouchEvents === false) return

    suppressClickUntil = 0
    event.preventDefault()
    event.stopImmediatePropagation()
  }

  function detach(element: HTMLElement) {
    window.removeEventListener('touchstart', onTouchStart, true)
    window.removeEventListener('touchmove', onTouchMove, true)
    window.removeEventListener('touchend', onTouchEnd, true)
    window.removeEventListener('touchcancel', onTouchCancel, true)
    element.removeEventListener('click', onClickCapture, true)
  }

  function attach(element: HTMLElement) {
    // Listen at the window during the active page lifetime so a second finger
    // that lands outside the container still cancels the one-finger gesture.
    window.addEventListener('touchstart', onTouchStart, {
      capture: true,
      passive: true,
    })
    window.addEventListener('touchmove', onTouchMove, {
      capture: true,
      passive: false,
    })
    window.addEventListener('touchend', onTouchEnd, {
      capture: true,
      passive: true,
    })
    window.addEventListener('touchcancel', onTouchCancel, {
      capture: true,
      passive: true,
    })
    element.addEventListener('click', onClickCapture, true)
  }

  watch(
    target,
    (nextTarget) => {
      lifecycleVersion += 1
      if (currentTarget) detach(currentTarget)

      currentTarget = nextTarget
      gesture = null
      suppressClickUntil = 0
      resetPull()
      refreshing.value = false

      if (nextTarget) attach(nextTarget)
    },
    { immediate: true, flush: 'sync' },
  )

  watch(
    () => options.disabled(),
    (isDisabled) => {
      if (isDisabled) {
        if (gesture?.claimed) suppressFollowingClick()
        cancelGesture()
      }
    },
    { flush: 'sync' },
  )

  onScopeDispose(() => {
    disposed = true
    lifecycleVersion += 1
    if (currentTarget) detach(currentTarget)
    currentTarget = null
    gesture = null
    suppressClickUntil = 0
    refreshing.value = false
    resetPull()
  })

  return {
    distance: readonly(distance),
    armed: readonly(armed),
    refreshing: readonly(refreshing),
  }
}
