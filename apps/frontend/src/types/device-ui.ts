import type { AppUser } from './app'

export type DeviceUser = Pick<AppUser, 'id' | 'role'> &
  Partial<Pick<AppUser, 'householdId'>>
export type DeviceCategory = 'esp32' | 'bardi'
export type SetupStatus = 'complete' | 'incomplete' | 'loading' | 'error'

export interface TabOption {
  value: string
  label: string
  panelId: string
  status?: SetupStatus
}

export interface DeviceGuideStep {
  id: string
  title: string
  description: string
  image: string
  imageAlt: string
}
