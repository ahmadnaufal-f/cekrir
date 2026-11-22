import type { SetupContent } from '../types/app'
import type { AppServices } from '../services/contracts'

export type SetupReferenceTarget = 'source' | 'guide'

const esp32Paths: Record<SetupReferenceTarget, string> = {
  source: 'apps/esp32/src/main.cpp',
  guide: 'apps/esp32/README.md',
}

export const esp32SetupContent: SetupContent = {
  kind: 'esp32',
  readiness: 'scaffold',
  sourceUrl: esp32Paths.source,
  guideUrl: esp32Paths.guide,
}

export const deviceGuideServices: Pick<AppServices, 'setup'> = {
  setup: {
    async content(kind) {
      return kind === 'esp32'
        ? esp32SetupContent
        : { kind, readiness: 'pending', sourceUrl: null, guideUrl: null }
    },
  },
}

const repository = 'https://github.com/ahmadnaufal-f/cekrir'
const scaffoldRevision = 'bc45600de0906a4b7995ac71118025259072c8a5'

/** Returns only repository references that are approved for this setup item. */
export function configuredReference(
  resource: SetupContent | null,
  target: SetupReferenceTarget,
): string | null {
  if (!resource) return null
  const reference = target === 'source' ? resource.sourceUrl : resource.guideUrl
  if (!reference) return null

  const relativePath = reference.replace(/^\/+/, '')
  if (resource.kind === 'esp32' && relativePath === esp32Paths[target]) {
    return `${repository}/blob/${scaffoldRevision}/${relativePath}`
  }

  try {
    const url = new URL(reference)
    if (
      url.protocol !== 'https:' ||
      url.origin !== 'https://github.com' ||
      url.username ||
      url.password ||
      url.search ||
      url.hash
    ) {
      return null
    }

    const prefix = '/ahmadnaufal-f/cekrir/blob/'
    if (!url.pathname.startsWith(prefix)) return null
    const pathAfterRevision = url.pathname
      .slice(prefix.length)
      .split('/')
      .slice(1)
      .join('/')

    if (resource.kind === 'esp32') {
      return pathAfterRevision === esp32Paths[target] ? url.toString() : null
    }

    // No BARDI guide is authored yet. Accept one only when the setup service
    // supplies a Markdown document in this repository's BARDI docs tree.
    const isBardiGuide =
      target === 'guide' &&
      /^(?:apps|docs)\/bardi\/[A-Za-z0-9._/-]+\.md$/.test(pathAfterRevision) &&
      !pathAfterRevision.split('/').includes('..')
    return isBardiGuide ? url.toString() : null
  } catch {
    return null
  }
}
