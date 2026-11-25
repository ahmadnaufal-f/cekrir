<script setup lang="ts">
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  shallowRef,
  useTemplateRef,
  watch,
} from 'vue'
import AppIcon from './AppIcon.vue'
import type { DeviceGuideStep } from '../types/device-ui'

const props = defineProps<{
  label: string
  steps: readonly DeviceGuideStep[]
}>()

const viewport = useTemplateRef<HTMLDivElement>('viewport')
const activeIndex = defineModel<number>('activeIndex', { default: 0 })
const slidePosition = shallowRef(activeIndex.value)
const progressLabel = computed(
  () => `Langkah ${activeIndex.value + 1} dari ${props.steps.length}`,
)
const progress = computed(() => (slidePosition.value + 1) / props.steps.length)

let resizeObserver: ResizeObserver | null = null
let animationFrame: number | null = null
let mounted = false

function reduceMotion(): boolean {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

function updateActiveIndex(): void {
  const element = viewport.value
  if (!element || element.clientWidth === 0) return
  slidePosition.value = Math.min(
    Math.max(element.scrollLeft / element.clientWidth, 0),
    props.steps.length - 1,
  )
  activeIndex.value = Math.round(slidePosition.value)
}

function queueActiveIndexUpdate(): void {
  if (animationFrame !== null) cancelAnimationFrame(animationFrame)
  animationFrame = requestAnimationFrame(() => {
    animationFrame = null
    updateActiveIndex()
  })
}

function alignActiveSlide(): void {
  const element = viewport.value
  if (!element) return
  element.scrollTo({
    left: activeIndex.value * element.clientWidth,
    behavior: 'auto',
  })
  updateActiveIndex()
}

function goTo(index: number, animate = true): void {
  const element = viewport.value
  if (!element) return
  const nextIndex = Math.min(Math.max(index, 0), props.steps.length - 1)
  element.scrollTo({
    left: nextIndex * element.clientWidth,
    behavior: animate && !reduceMotion() ? 'smooth' : 'instant',
  })
  updateActiveIndex()
}

function handleViewportKeydown(event: KeyboardEvent): void {
  if (event.altKey || event.ctrlKey || event.metaKey) return

  if (event.key === 'ArrowRight') {
    event.preventDefault()
    goTo(activeIndex.value + 1, false)
  } else if (event.key === 'ArrowLeft') {
    event.preventDefault()
    goTo(activeIndex.value - 1, false)
  } else if (event.key === 'Home') {
    event.preventDefault()
    goTo(0, false)
  } else if (event.key === 'End') {
    event.preventDefault()
    goTo(props.steps.length - 1, false)
  }
}

function handleResize(): void {
  alignActiveSlide()
}

watch(
  () => props.steps,
  () => {
    slidePosition.value = 0
    activeIndex.value = 0
    void nextTick(alignActiveSlide)
  },
  { flush: 'post' },
)

onMounted(() => {
  mounted = true
  const element = viewport.value
  if (!element) return

  element.addEventListener('scroll', queueActiveIndexUpdate, { passive: true })
  window.addEventListener('resize', handleResize)
  window.visualViewport?.addEventListener('resize', handleResize)
  document.fonts?.addEventListener('loadingdone', handleResize)

  if (typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver(handleResize)
    resizeObserver.observe(element)
  }

  void document.fonts?.ready.then(() => {
    if (mounted) handleResize()
  })
})

onBeforeUnmount(() => {
  mounted = false
  const element = viewport.value
  element?.removeEventListener('scroll', queueActiveIndexUpdate)
  window.removeEventListener('resize', handleResize)
  window.visualViewport?.removeEventListener('resize', handleResize)
  document.fonts?.removeEventListener('loadingdone', handleResize)
  resizeObserver?.disconnect()
  resizeObserver = null
  if (animationFrame !== null) cancelAnimationFrame(animationFrame)
})
</script>

<template>
  <section
    class="setup-step-carousel"
    role="region"
    aria-roledescription="carousel"
    :aria-label="label"
  >
    <div class="setup-step-carousel__topline">
      <p
        class="setup-step-carousel__progress"
        aria-live="polite"
        aria-atomic="true"
      >
        {{ progressLabel }}
      </p>
      <div
        class="setup-step-carousel__meter"
        role="progressbar"
        :aria-label="label"
        :aria-valuemin="1"
        :aria-valuemax="steps.length"
        :aria-valuenow="activeIndex + 1"
        :aria-valuetext="progressLabel"
      >
        <span :style="{ transform: `scaleX(${progress})` }"></span>
      </div>
    </div>

    <div
      ref="viewport"
      class="setup-step-carousel__viewport"
      role="group"
      tabindex="0"
      :aria-label="`${label}. Gunakan tombol panah kiri dan kanan untuk berpindah langkah.`"
      @keydown="handleViewportKeydown"
    >
      <article
        v-for="(step, index) in steps"
        :key="step.id"
        class="setup-step"
        role="group"
        aria-roledescription="slide"
        :aria-label="`Langkah ${index + 1} dari ${steps.length}`"
        :aria-hidden="index !== activeIndex"
        :inert="index !== activeIndex"
      >
        <figure class="setup-step__illustration">
          <img
            :src="step.image"
            :alt="step.imageAlt"
            width="800"
            height="500"
          />
        </figure>
        <div class="setup-step__copy">
          <h2>{{ step.title }}</h2>
          <p>{{ step.description }}</p>
        </div>
      </article>
    </div>

    <div class="setup-step-carousel__controls">
      <nav class="setup-step-carousel__pagination" aria-label="Pilih langkah">
        <button
          v-for="(step, index) in steps"
          :key="step.id"
          type="button"
          class="setup-step-carousel__dot"
          :class="{ 'setup-step-carousel__dot--active': index === activeIndex }"
          :aria-label="`Tampilkan langkah ${index + 1}: ${step.title}`"
          :aria-current="index === activeIndex ? 'step' : undefined"
          @click="goTo(index, $event.detail > 0)"
        >
          <span></span>
        </button>
      </nav>
      <div class="setup-step-carousel__arrows">
        <button
          type="button"
          class="setup-step-carousel__arrow"
          :disabled="activeIndex === 0"
          @click="goTo(activeIndex - 1, $event.detail > 0)"
        >
          <AppIcon name="back" />
          Sebelumnya
        </button>
        <button
          type="button"
          class="setup-step-carousel__arrow setup-step-carousel__arrow--next"
          :disabled="activeIndex === steps.length - 1"
          @click="goTo(activeIndex + 1, $event.detail > 0)"
        >
          Berikutnya
          <AppIcon name="next" />
        </button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.setup-step-carousel {
  overflow: hidden;
  border: 1px solid #dce3d7;
  border-radius: 14px;
  background: #fffefa;
  color: #233d37;
}

.setup-step-carousel__topline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 18px var(--card-inset) 14px;
}

.setup-step-carousel__progress {
  color: #53675a;
  font-size: 0.8125rem;
  font-weight: 650;
  font-variant-numeric: tabular-nums;
}

.setup-step-carousel__meter {
  width: min(170px, 36%);
  height: 6px;
  overflow: hidden;
  border-radius: 99px;
  background: #e6ebe2;
}

.setup-step-carousel__meter span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: #588264;
  transform-origin: left;
}

.setup-step-carousel__viewport {
  display: flex;
  overflow-x: auto;
  overflow-y: hidden;
  overscroll-behavior-x: contain;
  scroll-snap-type: x mandatory;
  scrollbar-width: none;
  touch-action: pan-x pan-y pinch-zoom;
  -webkit-overflow-scrolling: touch;
}

.setup-step-carousel__viewport::-webkit-scrollbar {
  display: none;
}

.setup-step-carousel__viewport:focus-visible {
  outline: 3px solid #b88736;
  outline-offset: -3px;
}

.setup-step {
  display: grid;
  flex: 0 0 100%;
  grid-template-columns: minmax(0, 1.04fr) minmax(0, 0.96fr);
  align-items: center;
  gap: clamp(24px, 4vw, 48px);
  min-width: 100%;
  min-height: 336px;
  padding: 12px var(--card-inset) 30px;
  scroll-snap-align: start;
  scroll-snap-stop: always;
}

.setup-step__illustration {
  width: 100%;
  max-width: 420px;
  justify-self: center;
  margin: 0;
  overflow: hidden;
  border: 1px solid #dce3d7;
  border-radius: 12px;
  background: #f6f7f2;
  aspect-ratio: 16 / 10;
}

.setup-step__illustration img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.setup-step__copy {
  max-width: 52ch;
}

.setup-step__copy h2 {
  margin: 0;
  color: #233d37;
  font-size: clamp(1.25rem, 2.2vw, 1.75rem);
  font-weight: 680;
  letter-spacing: -0.035em;
  line-height: 1.2;
  text-wrap: balance;
}

.setup-step__copy p {
  margin: 14px 0 0;
  color: #53675a;
  font-size: 0.9375rem;
  line-height: 1.75;
}

.setup-step-carousel__controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 14px var(--card-inset) 18px;
  border-top: 1px solid #e8ece4;
}

.setup-step-carousel__pagination,
.setup-step-carousel__arrows {
  display: flex;
  align-items: center;
}

.setup-step-carousel__arrows {
  flex-wrap: wrap;
  gap: 8px;
}

.setup-step-carousel__dot {
  display: grid;
  width: 44px;
  height: 44px;
  place-items: center;
  padding: 0;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: inherit;
}

.setup-step-carousel__dot span {
  width: 22px;
  height: 9px;
  border-radius: 99px;
  background: #c4d0c0;
  transform: scaleX(0.41);
}

.setup-step-carousel__dot--active span {
  background: #234e41;
  transform: scaleX(1);
}

.setup-step-carousel__arrow {
  display: inline-flex;
  min-height: 44px;
  align-items: center;
  justify-content: center;
  gap: 7px;
  padding: 9px 12px;
  border: 1px solid #d6dfd2;
  border-radius: 8px;
  background: #fffefa;
  color: #234e41;
  font-size: 0.8125rem;
  font-weight: 650;
}

.setup-step-carousel__arrow:active:not(:disabled) {
  background: #f0f3eb;
}

@media (hover: hover) and (pointer: fine) {
  .setup-step-carousel__dot:hover:not(.setup-step-carousel__dot--active) span {
    background: #8fa48b;
  }

  .setup-step-carousel__arrow:hover:not(:disabled) {
    background: #f0f3eb;
  }
}

@media (prefers-reduced-motion: no-preference) {
  .setup-step-carousel__dot span,
  .setup-step-carousel__arrow {
    transition:
      transform var(--motion-feedback) var(--ease-enter),
      background-color var(--motion-feedback) ease;
  }

  .setup-step-carousel__arrow:active:not(:disabled) {
    transform: scale(0.96);
  }
}

.setup-step-carousel__arrow:disabled {
  cursor: default;
  color: #647468;
  opacity: 0.58;
}

@media (max-width: 680px) {
  .setup-step-carousel__topline {
    padding-block: 15px 12px;
  }

  .setup-step {
    grid-template-columns: minmax(0, 1fr);
    gap: 20px;
    min-height: 0;
    padding-block: 8px 24px;
  }

  .setup-step__illustration {
    max-width: none;
  }

  .setup-step__copy h2 {
    font-size: 1.25rem;
  }

  .setup-step__copy p {
    margin-top: 9px;
    font-size: 0.875rem;
    line-height: 1.65;
  }

  .setup-step-carousel__controls {
    align-items: flex-start;
    flex-direction: column;
    gap: 8px;
    padding-block: 11px 15px;
  }

  .setup-step-carousel__pagination {
    align-self: center;
    flex-wrap: wrap;
    justify-content: center;
  }

  .setup-step-carousel__arrows {
    width: 100%;
    justify-content: space-between;
  }

  .setup-step-carousel__arrow {
    padding-inline: 8px;
  }
}
</style>
