<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from './AppIcon.vue'
import SkeletonBlock from './SkeletonBlock.vue'
import { deliveryCopy as copy } from '../lib/delivery-copy'
import type { DeliveryTotals, DeliveryTotalsQuery } from '../types/app'

const props = defineProps<{
  query: DeliveryTotalsQuery
  totals: DeliveryTotals | null
  pending: boolean
  failed: boolean
}>()
const emit = defineEmits<{ retry: [] }>()
const dayLabel = computed(() => {
  const [year, month, day] = props.query.date.split('-').map(Number)
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeZone: 'UTC',
  }).format(new Date(Date.UTC(year!, month! - 1, day!)))
})
const number = new Intl.NumberFormat()
</script>

<template>
  <section
    class="delivery-summary"
    aria-labelledby="delivery-summary-title"
    :aria-busy="pending"
  >
    <header class="delivery-summary__header">
      <h2 id="delivery-summary-title">{{ copy.summaryTitle }}</h2>
      <time :datetime="query.date">{{ dayLabel }}</time>
    </header>
    <dl class="delivery-summary__totals">
      <div>
        <dt>{{ copy.summaryToday }}</dt>
        <dd
          class="delivery-summary__today"
          :aria-label="pending ? copy.summaryLoading : undefined"
        >
          <SkeletonBlock
            v-if="pending"
            class="delivery-summary__value-skeleton"
          />
          <template v-else
            >{{ totals ? number.format(totals.receivedToday) : '—'
            }}<span class="delivery-summary__unit">{{
              copy.summaryUnit
            }}</span></template
          >
        </dd>
      </div>
      <div>
        <dt>{{ copy.summaryAllTime }}</dt>
        <dd
          class="delivery-summary__all-time"
          :aria-label="pending ? copy.summaryLoading : undefined"
        >
          <SkeletonBlock
            v-if="pending"
            class="delivery-summary__value-skeleton"
          />
          <template v-else
            >{{ totals ? number.format(totals.receivedAllTime) : '—'
            }}<span class="delivery-summary__unit">{{
              copy.summaryUnit
            }}</span></template
          >
        </dd>
      </div>
    </dl>
    <div v-if="failed && !pending" class="delivery-summary__error" role="alert">
      <p>{{ copy.summaryLoadError }}</p>
      <button type="button" class="text-button" @click="emit('retry')">
        <AppIcon name="refresh" />{{ copy.summaryRetry }}
      </button>
    </div>
    <p v-else class="delivery-summary__note">{{ copy.summaryDateHint }}</p>
  </section>
</template>

<style scoped>
.delivery-summary {
  container: package-summary / inline-size;
  font-size: 1rem;
  margin-bottom: 30px;
  padding-block: 22px;
  padding-inline: var(--card-inset);
  border: 1px solid #dfe4d9;
  border-radius: 12px;
  background: #fffefa;
}
.delivery-summary__header {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px 16px;
  margin-bottom: 22px;
}
.delivery-summary__header h2 {
  margin: 0;
  font-size: 1.0625rem;
}
.delivery-summary__header time,
.delivery-summary__note {
  color: #53675a;
  font-size: 0.8125rem;
  line-height: 1.5;
}
.delivery-summary__totals {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  margin: 0;
}
.delivery-summary__totals > div + div {
  border-left: 1px solid #e4e8df;
  padding-left: 24px;
}
.delivery-summary__totals > div {
  display: flex;
  min-width: 0;
  flex-direction: column;
  justify-content: space-between;
}
.delivery-summary__totals dt {
  overflow-wrap: anywhere;
  color: #53675a;
  font-size: 0.875rem;
  line-height: 1.5;
}
.delivery-summary__totals dd {
  min-height: 1.25em;
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 7px;
  margin: 6px 0 0;
  font-size: 2rem;
  font-weight: 650;
  font-variant-numeric: tabular-nums;
  line-height: 1.25;
  overflow-wrap: anywhere;
}
.delivery-summary__unit {
  color: #53675a;
  font-size: 0.8125rem;
  font-weight: 400;
}
.delivery-summary .delivery-summary__value-skeleton {
  width: 2em;
  height: 1em;
  border-radius: 6px;
}
.delivery-summary__note,
.delivery-summary__error {
  margin-top: 18px;
}
.delivery-summary__error {
  color: #875334;
  font-size: 0.875rem;
  line-height: 1.5;
}
.delivery-summary__error .text-button {
  padding-left: 0;
}
@media (max-width: 640px) {
  .delivery-summary {
    padding-block: 20px;
  }
  .delivery-summary__totals > div + div {
    padding-left: 16px;
  }
}
@container package-summary (max-width: 14em) {
  .delivery-summary__totals {
    grid-template-columns: 1fr;
  }
  .delivery-summary__totals > div + div {
    padding-top: 16px;
    padding-left: 0;
    border-top: 1px solid #e4e8df;
    border-left: 0;
  }
}
</style>
