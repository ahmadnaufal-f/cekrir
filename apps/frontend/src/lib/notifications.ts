import { Capacitor } from '@capacitor/core'
import {
  LocalNotifications,
  type LocalNotificationSchema,
} from '@capacitor/local-notifications'
import type { PackageNotification } from '../types/api'

const shipmentTestNotificationId = 53001
const tapPayloadType = 'cekrir-shipment'

export interface NotificationShipmentTarget {
  accountId: string
  shipmentId: string
  kind: 'test' | 'report'
}

export function canSendDeviceNotification(): boolean {
  return (
    Capacitor.isNativePlatform() &&
    Capacitor.isPluginAvailable('LocalNotifications')
  )
}

export async function requestNotificationPermission(): Promise<boolean> {
  const { display } = await LocalNotifications.checkPermissions()
  if (display === 'granted') return true
  if (display === 'denied') return false
  return (await LocalNotifications.requestPermissions()).display === 'granted'
}

async function sendDeviceNotification(
  notification: LocalNotificationSchema,
  channel: { id: string; name: string },
  canDeliver: () => boolean,
) {
  if (!canDeliver()) return
  const android = Capacitor.getPlatform() === 'android'
  if (android) {
    await LocalNotifications.createChannel({ ...channel, importance: 4 })
  }
  if (!canDeliver()) return
  await LocalNotifications.schedule({
    notifications: [
      {
        ...notification,
        foreground: true,
        isExactNotification: false,
        autoCancel: true,
        ...(android ? { channelId: channel.id } : {}),
      },
    ],
  })
}

export function scheduleTestNotification(
  accountId: string,
  shipmentId: string | undefined,
  canDeliver: () => boolean = () => true,
) {
  return sendDeviceNotification(
    {
      id: shipmentTestNotificationId,
      title: 'Tes notifikasi paket',
      body: shipmentId
        ? 'Ketuk untuk membuka detail paket di Cekrir.'
        : 'Ini adalah contoh notifikasi paket dari Cekrir.',
      extra: {
        type: tapPayloadType,
        kind: 'test',
        accountId,
        ...(shipmentId ? { shipmentId } : {}),
      },
    },
    { id: 'shipment-notification-tests', name: 'Tes notifikasi paket' },
    canDeliver,
  )
}

export async function showPackageNotification(
  accountId: string,
  notification: PackageNotification,
  canDeliver: () => boolean,
) {
  if (!canSendDeviceNotification() || !canDeliver()) return
  if ((await LocalNotifications.checkPermissions()).display !== 'granted')
    return

  const hash = [...`${accountId}:${notification.id}`].reduce(
    (value, char) => (value * 31 + char.charCodeAt(0)) | 0,
    0,
  )
  const id = hash & 0x7fffffff || 1
  await sendDeviceNotification(
    {
      id: id === shipmentTestNotificationId ? id + 1 : id,
      title: notification.title,
      body: 'Ketuk untuk membuka detail paket di Cekrir.',
      extra: {
        type: tapPayloadType,
        kind: 'report',
        accountId,
        shipmentId: notification.shipment_id,
      },
    },
    { id: 'shipment-reports', name: 'Notifikasi paket' },
    canDeliver,
  )
}

export function listenForShipmentNotificationTaps(
  open: (target: NotificationShipmentTarget) => void,
): () => void {
  if (!canSendDeviceNotification()) return () => {}

  let active = true
  const listener = LocalNotifications.addListener(
    'localNotificationActionPerformed',
    ({ actionId, notification }) => {
      if (!active || actionId !== 'tap') return
      const extra: unknown = notification.extra
      if (
        extra &&
        typeof extra === 'object' &&
        'type' in extra &&
        extra.type === tapPayloadType &&
        'kind' in extra &&
        (extra.kind === 'test' || extra.kind === 'report') &&
        'accountId' in extra &&
        typeof extra.accountId === 'string' &&
        extra.accountId &&
        'shipmentId' in extra &&
        typeof extra.shipmentId === 'string' &&
        extra.shipmentId
      )
        open({
          accountId: extra.accountId,
          shipmentId: extra.shipmentId,
          kind: extra.kind,
        })
    },
  ).catch(() => undefined)

  return () => {
    active = false
    void listener.then((handle) => handle?.remove()).catch(() => undefined)
  }
}
