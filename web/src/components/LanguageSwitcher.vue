<template>
  <div class="language-dropdown">
    <i class="fas fa-globe language-icon"></i>
    <select v-model="currentLanguage" @change="changeLanguage" class="language-select">
      <option value="en">English</option>
      <option value="zh">中文</option>
    </select>
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
.language-dropdown {
  position: relative;
  display: flex;
  align-items: center;
  background: transparent;
  border: 1px solid var(--border-color);
  color: var(--secondary-color);
  padding: 0;
  border-radius: var(--border-radius);
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 500;
  transition: all 0.2s ease;
  gap: 0.5rem;
  height: 36px;
  box-sizing: border-box;
  padding-left: 0.8rem;
  padding-right: 0.8rem;
}

.language-dropdown:hover {
  border-color: var(--danger-color);
  color: var(--danger-color);
  background-color: rgba(245, 108, 108, 0.05);
}

.language-icon {
  font-size: 0.9rem;
  color: inherit;
  pointer-events: none;
  flex-shrink: 0;
  height: 32px;
  line-height: 32px;
}

.language-select {
  background: transparent;
  border: none;
  outline: none;
  color: inherit;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  min-width: 70px;
  font-family: inherit;
  height: 32px;
  line-height: 32px;
  margin: 0;
  padding: 0;
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