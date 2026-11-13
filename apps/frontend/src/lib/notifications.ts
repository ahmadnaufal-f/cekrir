import { Capacitor } from '@capacitor/core'
import { LocalNotifications } from '@capacitor/local-notifications'
import type { PackageNotification } from '../types/api'

export async function requestNotificationPermission(): Promise<boolean> {
  if (Capacitor.isNativePlatform()) {
    const result = await LocalNotifications.requestPermissions()
    return result.display === 'granted'
  }
  if (!('Notification' in window)) return false
  return (await Notification.requestPermission()) === 'granted'
}

export async function showPackageNotification(
  notification: PackageNotification,
): Promise<void> {
  if (Capacitor.isNativePlatform()) {
    // Stable positive 31-bit ID, within Capacitor's Android notification ID range.
    const hash = [...notification.id].reduce(
      (value, char) => (value * 31 + char.charCodeAt(0)) | 0,
      0,
    )
    await LocalNotifications.schedule({
      notifications: [
        {
          id: hash & 0x7fffffff || 1,
          title: notification.title,
          body: notification.message,
        },
      ],
    })
  } else if (
    'Notification' in window &&
    Notification.permission === 'granted'
  ) {
    new Notification(notification.title, {
      body: notification.message,
      tag: notification.id,
    })
  }
}
