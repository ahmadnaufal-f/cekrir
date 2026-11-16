import type { DeliveryDetail, DeviceInventory } from '../types/app'

/** This is a labelled illustration for the demo, never a CCTV or delivery photo. */
export const DEMO_DELIVERY_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 600" role="img" aria-labelledby="title description">
  <title id="title">Ilustrasi paket demo</title>
  <desc id="description">Ilustrasi paket untuk demonstrasi, bukan foto CCTV atau foto pengiriman nyata.</desc>
  <rect width="960" height="600" rx="32" fill="#eef4f0"/>
  <circle cx="760" cy="150" r="90" fill="#dcebe3"/>
  <path d="M0 460 230 350l170 95 190-145 370 170v130H0Z" fill="#d7e5dc"/>
  <rect x="286" y="204" width="386" height="274" rx="20" fill="#c78b56"/>
  <path d="m286 224 193 122 193-122M479 346v132" fill="none" stroke="#9d6840" stroke-width="18"/>
  <path d="m404 205 75 48 75-48" fill="none" stroke="#f0c894" stroke-width="18"/>
  <rect x="403" y="370" width="152" height="58" rx="10" fill="#fffaf0"/>
  <text x="479" y="396" text-anchor="middle" font-family="Arial,sans-serif" font-size="14" font-weight="700" fill="#385446">PAKET DEMO</text>
  <text x="479" y="415" text-anchor="middle" font-family="Arial,sans-serif" font-size="10" fill="#577061">ILUSTRASI</text>
  <rect x="54" y="42" width="852" height="66" rx="18" fill="#173d32"/>
  <text x="480" y="84" text-anchor="middle" font-family="Arial,sans-serif" font-size="22" font-weight="700" letter-spacing="1" fill="#fff">DEMO · ILUSTRASI · BUKAN FOTO CCTV</text>
  <text x="480" y="548" text-anchor="middle" font-family="Arial,sans-serif" font-size="16" fill="#385446">Gambar simulasi untuk pratinjau layanan</text>
</svg>`

export const MOCK_DEMO_ACCOUNTS = Object.freeze({
  admin: { loginId: 'admin@demo.test', password: 'demo1234' },
  member: { loginId: 'anggota', password: 'demo1234' },
  otherHousehold: { loginId: 'tetangga', password: 'demo1234' },
})

export const MOCK_DELIVERY_IDS = Object.freeze({
  complete: 'delivery-demo-complete',
  photoUnavailable: 'delivery-demo-photo-unavailable',
  trackingUnavailable: 'delivery-demo-tracking-unavailable',
  bothUnavailable: 'delivery-demo-both-unavailable',
  pending: 'delivery-demo-pending',
})

const deliveryCases: Array<{
  id: string
  photoState: DeliveryDetail['photoState']
  trackingState: DeliveryDetail['trackingState']
  label: string
}> = [
  {
    id: MOCK_DELIVERY_IDS.complete,
    photoState: 'ready',
    trackingState: 'ready',
    label: 'Paket Demo 01',
  },
  {
    id: MOCK_DELIVERY_IDS.photoUnavailable,
    photoState: 'unavailable',
    trackingState: 'ready',
    label: 'Paket Demo 02',
  },
  {
    id: MOCK_DELIVERY_IDS.trackingUnavailable,
    photoState: 'ready',
    trackingState: 'unavailable',
    label: 'Paket Demo 03',
  },
  {
    id: MOCK_DELIVERY_IDS.bothUnavailable,
    photoState: 'unavailable',
    trackingState: 'unavailable',
    label: 'Paket Demo 04',
  },
  {
    id: MOCK_DELIVERY_IDS.pending,
    photoState: 'pending',
    trackingState: 'pending',
    label: 'Paket Demo 05',
  },
  {
    id: 'delivery-demo-photo-pending',
    photoState: 'pending',
    trackingState: 'ready',
    label: 'Paket Demo 06',
  },
  {
    id: 'delivery-demo-tracking-pending',
    photoState: 'ready',
    trackingState: 'pending',
    label: 'Paket Demo 07',
  },
  {
    id: 'delivery-demo-photo-pending-tracking-unavailable',
    photoState: 'pending',
    trackingState: 'unavailable',
    label: 'Paket Demo 08',
  },
  {
    id: 'delivery-demo-photo-unavailable-tracking-pending',
    photoState: 'unavailable',
    trackingState: 'pending',
    label: 'Paket Demo 09',
  },
]

function createTracking(
  index: number,
): NonNullable<DeliveryDetail['tracking']> {
  return {
    service: 'SPX Express (data simulasi)',
    statusCode: 'DEMO_RECEIVED',
    statusLabel: 'Contoh status pelacakan',
    senderName: 'Pengirim Demo',
    recipientName: 'Penerima Demo',
    origin: 'Kota Contoh',
    destination: 'Lokasi Demo',
    events: [
      {
        occurredAt: `2026-11-15T0${8 - Math.min(index, 7)}:30:00Z`,
        description: 'Peristiwa pelacakan contoh',
        location: 'Lokasi Simulasi',
      },
    ],
  }
}

export const DEMO_DELIVERIES: readonly DeliveryDetail[] = Object.freeze(
  deliveryCases.map((fixture, index) => ({
    id: fixture.id,
    householdId: 'household-demo',
    trackingNumber: `DEMO-SPX-${String(1001 + index)}`,
    courier: { code: 'spx-demo', name: 'SPX Express (demo)' },
    scannedAt: new Date(
      Date.UTC(2026, 10, 15, 8, 50 - index * 5),
    ).toISOString(),
    photoState: fixture.photoState,
    trackingState: fixture.trackingState,
    photoContentPath:
      fixture.photoState === 'ready' ? 'mock:demo-delivery.svg' : null,
    tracking: fixture.trackingState === 'ready' ? createTracking(index) : null,
  })),
)

export const OTHER_HOUSEHOLD_DELIVERY: DeliveryDetail = Object.freeze({
  id: 'delivery-tetangga-complete',
  householdId: 'household-tetangga',
  trackingNumber: 'DEMO-SPX-2001',
  courier: { code: 'spx-demo', name: 'SPX Express (demo)' },
  scannedAt: '2026-11-15T07:30:00.000Z',
  photoState: 'ready',
  trackingState: 'ready',
  photoContentPath: 'mock:demo-delivery.svg',
  tracking: createTracking(0),
})

export const INITIAL_DEMO_INVENTORY: DeviceInventory = Object.freeze({
  esp32: null,
  cameras: [
    {
      id: 'camera-demo-porch',
      name: 'Kamera Teras Demo',
      configurationState: 'configured',
      verificationState: 'not_tested',
    },
    {
      id: 'camera-demo-garage',
      name: 'Kamera Garasi Demo',
      configurationState: 'incomplete',
      verificationState: 'not_tested',
    },
  ],
  selectedDeliveryCameraId: null,
} as DeviceInventory)
