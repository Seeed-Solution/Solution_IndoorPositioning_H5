<template>
  <div id="app-shell">
    <nav class="main-nav">
      <!-- <router-link to="/" class="nav-link">Live Map</router-link> REMOVE THIS -->
      <router-link to="/config-master" class="nav-link">Map & Beacon Configuration</router-link>
      <router-link to="/config-local" class="nav-link">Local Mode</router-link>
      <router-link to="/config-tracker" class="nav-link">Tracker Mode</router-link>
    </nav>
    <router-view />
  </div>
</template>

<script setup>
// No script needed for this basic shell if it only contains router-view and links.
</script>

<style scoped>
#app-shell {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  /* background-color: var(--background-color); /* Optionally set body bg here if not taking full page */
}

.main-nav {
  background-color: var(--dark-color); /* Use theme variable */
  padding: 0.75rem 1.5rem; /* Consistent padding */
  display: flex;
  /* gap: 1rem; */ /* Consistent gap - removed to allow router-links to space themselves or use margins */
  justify-content: center; /* Center nav items */
  box-shadow: 0 2px 4px rgba(0,0,0,0.1); /* Add a subtle shadow */
}

.nav-link {
  color: var(--light-color); /* Light text on dark background */
  text-decoration: none;
  padding: 0.5rem 1rem;
  margin: 0 0.5rem; /* Added margin for spacing between links */
  border-radius: var(--border-radius);
  transition: background-color 0.2s ease;
  font-weight: 500;
}

.nav-link:hover,
.nav-link.router-link-exact-active {
  background-color: var(--primary-color); /* Use primary color for active/hover */
  color: white;
}

/* The <router-view /> itself doesn't need styling unless it's wrapped */
/* Content inside router-view should have its own padding via .page-container or similar */
</style>
