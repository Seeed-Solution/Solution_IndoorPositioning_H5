<template>
  <div class="language-switcher">
    <div class="language-dropdown">
      <i class="fas fa-globe language-icon"></i>
      <select v-model="currentLanguage" @change="changeLanguage" class="language-select">
        <option value="en">English</option>
        <option value="zh">中文</option>
      </select>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const { locale } = useI18n()

const currentLanguage = computed({
  get: () => locale.value,
  set: (value) => {
    locale.value = value
    localStorage.setItem('app-locale', value)
  }
})

const changeLanguage = (event) => {
  currentLanguage.value = event.target.value
}
</script>

<style scoped>
.language-switcher {
  display: flex;
  align-items: center;
}

.language-dropdown {
  position: relative;
  display: flex;
  align-items: center;
  background-color: transparent;
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 0.4rem 0.6rem;
  gap: 0.5rem;
  transition: all 0.2s ease;
}

.language-dropdown:hover {
  border-color: var(--primary-color);
  background-color: rgba(0, 86, 179, 0.05);
}

.language-icon {
  font-size: 0.8rem;
  color: var(--secondary-color);
  pointer-events: none;
}

.language-select {
  background: transparent;
  border: none;
  outline: none;
  color: var(--text-color);
  font-size: 0.9rem;
  cursor: pointer;
  min-width: 70px;
  font-family: inherit;
}

.language-select:focus {
  outline: none;
}

.language-select option {
  background-color: var(--card-background);
  color: var(--text-color);
  padding: 0.5rem;
}

/* 去掉默认的下拉箭头样式（在某些浏览器中） */
.language-select {
  -webkit-appearance: none;
  -moz-appearance: none;
  appearance: none;
}
</style>