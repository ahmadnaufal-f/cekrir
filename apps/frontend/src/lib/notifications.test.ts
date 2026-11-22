import { Capacitor } from '@capacitor/core'
import { LocalNotifications } from '@capacitor/local-notifications'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  canSendDeviceNotification,
  listenForShipmentNotificationTaps,
  requestNotificationPermission,
  scheduleTestNotification,
  showPackageNotification,
} from './notifications'

vi.mock('@capacitor/core', () => ({
  Capacitor: {
    isNativePlatform: vi.fn(),
    isPluginAvailable: vi.fn(),
    getPlatform: vi.fn(),
  },
}))
vi.mock('@capacitor/local-notifications', () => ({
  LocalNotifications: {
    checkPermissions: vi.fn(),
    requestPermissions: vi.fn(),
    createChannel: vi.fn(),
    schedule: vi.fn(),
    addListener: vi.fn(),
  },
}))

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(Capacitor.isNativePlatform).mockReturnValue(true)
  vi.mocked(Capacitor.isPluginAvailable).mockReturnValue(true)
})

describe('device notification test', () => {
  it('does not use the native plugin on the web', () => {
    vi.mocked(Capacitor.isNativePlatform).mockReturnValue(false)
    expect(canSendDeviceNotification()).toBe(false)
    const stop = listenForShipmentNotificationTaps(vi.fn())
    stop()
    expect(LocalNotifications.addListener).not.toHaveBeenCalled()
  })

  it('requests notification permission only when it can be prompted', async () => {
    vi.mocked(LocalNotifications.checkPermissions)
      .mockResolvedValueOnce({ display: 'denied' })
      .mockResolvedValueOnce({ display: 'prompt' })
    vi.mocked(LocalNotifications.requestPermissions).mockResolvedValue({
      display: 'granted',
    })

    await expect(requestNotificationPermission()).resolves.toBe(false)
    expect(LocalNotifications.requestPermissions).not.toHaveBeenCalled()
    await expect(requestNotificationPermission()).resolves.toBe(true)
    expect(LocalNotifications.requestPermissions).toHaveBeenCalledTimes(1)
  })

  it('sends an immediate Android notification with an account-scoped shipment link', async () => {
    vi.mocked(Capacitor.getPlatform).mockReturnValue('android')
    await scheduleTestNotification('account-1', 'shipment-1')

    expect(LocalNotifications.createChannel).toHaveBeenCalledWith({
      id: 'shipment-notification-tests',
      name: 'Tes notifikasi paket',
      importance: 4,
    })
    const { notifications } = vi.mocked(LocalNotifications.schedule).mock
      .calls[0]![0]
    expect(notifications).toEqual([
      expect.objectContaining({
        channelId: 'shipment-notification-tests',
        extra: {
          type: 'cekrir-shipment',
          kind: 'test',
          accountId: 'account-1',
          shipmentId: 'shipment-1',
        },
        foreground: true,
        isExactNotification: false,
      }),
    ])
    expect(notifications[0]).not.toHaveProperty('schedule')
  })

  it('accepts only taps carrying this test notification’s shipment payload', async () => {
    vi.mocked(Capacitor.getPlatform).mockReturnValue('ios')
    const onTap = vi.fn()
    const remove = vi.fn().mockResolvedValue(undefined)
    vi.mocked(LocalNotifications.addListener).mockResolvedValue({ remove })
    const stop = listenForShipmentNotificationTaps(onTap)
    await scheduleTestNotification('account-1', 'shipment-1')
    expect(LocalNotifications.createChannel).not.toHaveBeenCalled()
    const {
      notifications: [notification],
    } = vi.mocked(LocalNotifications.schedule).mock.calls[0]![0]
    const dispatch = vi.mocked(LocalNotifications.addListener).mock.calls[0]![1]

    dispatch({ actionId: 'dismiss', notification: notification! })
    dispatch({ actionId: 'tap', notification: { ...notification!, extra: {} } })
    dispatch({
      actionId: 'tap',
      notification: { ...notification!, extra: { accountId: 'account-1' } },
    })
    expect(onTap).not.toHaveBeenCalled()
    dispatch({ actionId: 'tap', notification: notification! })
    expect(onTap).toHaveBeenCalledExactlyOnceWith({
      accountId: 'account-1',
      shipmentId: 'shipment-1',
      kind: 'test',
    })
    stop()
    await vi.waitFor(() => expect(remove).toHaveBeenCalledOnce())
  })

  it('sends reports only when the account setting and device permission allow it', async () => {
    vi.mocked(Capacitor.getPlatform).mockReturnValue('android')
    const report = {
      id: 'report-1',
      shipment_id: 'shipment-1',
      title: 'Paket terdeteksi',
      message: 'Paket dengan resi DEMO-NEW-001 terdeteksi.',
      created_at: '2026-11-19T08:00:00Z',
    }
    await showPackageNotification('account-1', report, () => false)
    expect(LocalNotifications.checkPermissions).not.toHaveBeenCalled()
    vi.mocked(LocalNotifications.checkPermissions).mockResolvedValue({
      display: 'denied',
    })
    await showPackageNotification('account-1', report, () => true)
    expect(LocalNotifications.schedule).not.toHaveBeenCalled()
    expect(LocalNotifications.requestPermissions).not.toHaveBeenCalled()

    vi.mocked(LocalNotifications.checkPermissions).mockResolvedValue({
      display: 'granted',
    })
    await showPackageNotification('account-1', report, () => true)
    expect(LocalNotifications.schedule).toHaveBeenCalledWith({
      notifications: [
        expect.objectContaining({
          title: report.title,
          channelId: 'shipment-reports',
          extra: {
            type: 'cekrir-shipment',
            kind: 'report',
            accountId: 'account-1',
            shipmentId: 'shipment-1',
          },
        }),
      ],
    })
  })
})
