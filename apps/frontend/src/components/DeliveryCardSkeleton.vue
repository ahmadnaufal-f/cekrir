<script setup lang="ts">
import SkeletonBlock from './SkeletonBlock.vue'
</script>

<template>
  <div class="delivery-card-skeleton" aria-hidden="true">
    <div class="delivery-card-skeleton__information">
      <SkeletonBlock class="delivery-card-skeleton__number" />
      <SkeletonBlock class="delivery-card-skeleton__courier" />
      <SkeletonBlock class="delivery-card-skeleton__time" />
    </div>

    <div class="delivery-card-skeleton__resources">
      <span class="delivery-card-skeleton__resource">
        <SkeletonBlock class="delivery-card-skeleton__resource-icon" />
        <SkeletonBlock class="delivery-card-skeleton__resource-label--photo" />
      </span>
      <span class="delivery-card-skeleton__resource">
        <SkeletonBlock class="delivery-card-skeleton__resource-icon" />
        <SkeletonBlock
          class="delivery-card-skeleton__resource-label--tracking"
        />
      </span>
    </div>
  </div>
</template>

<style scoped>
.delivery-card-skeleton {
  display: flex;
  width: 100%;
  min-width: 0;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding-block: 22px;
  padding-inline: var(--card-inset);
  border: 1px solid #dfe4d9;
  border-radius: 12px;
  background: #fffefa;
}

.delivery-card-skeleton__information {
  display: grid;
  min-width: 0;
  gap: 5px;
  flex: 1 1 auto;
}

.delivery-card-skeleton .delivery-card-skeleton__number {
  width: 13rem;
  max-width: 100%;
  height: 1.4em;
}

.delivery-card-skeleton .delivery-card-skeleton__courier {
  width: 8rem;
  max-width: 100%;
  height: 1.5em;
  font-size: 0.875rem;
}

.delivery-card-skeleton .delivery-card-skeleton__time {
  width: 11rem;
  max-width: 100%;
  height: 1.5em;
  margin-top: 3px;
  font-size: 0.8125rem;
}

.delivery-card-skeleton__resources {
  display: flex;
  max-width: 100%;
  flex: 0 0 auto;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
}

.delivery-card-skeleton__resource {
  display: inline-flex;
  max-width: 100%;
  align-items: center;
  gap: 5px;
  padding: 4px 8px;
  border-radius: 999px;
  background: #f0f2e9;
  line-height: 1.25;
}

.delivery-card-skeleton .delivery-card-skeleton__resource-icon {
  width: 1rem;
  max-width: 1rem;
  height: 1rem;
  border-radius: 50%;
}

.delivery-card-skeleton .delivery-card-skeleton__resource-label--photo {
  width: 2rem;
  max-width: 2rem;
  height: 0.8125rem;
}

.delivery-card-skeleton .delivery-card-skeleton__resource-label--tracking {
  width: 4rem;
  max-width: 4rem;
  height: 0.8125rem;
}

@media (max-width: 640px) {
  .delivery-card-skeleton {
    align-items: flex-start;
    flex-direction: column;
    gap: 14px;
    padding-block: 20px;
  }

  .delivery-card-skeleton__information {
    width: 100%;
    flex: none;
  }

  .delivery-card-skeleton__resources {
    justify-content: flex-start;
  }
}
</style>
