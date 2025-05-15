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
  background-color: var(--card-background); /* Changed from --dark-color to white */
  padding: 0.75rem 1.5rem;
  display: flex;
  justify-content: center;
  box-shadow: 0 2px 4px rgba(0,0,0,0.08); /* Adjusted shadow for white bg */
  border-bottom: 1px solid var(--border-color); /* Added a light border like SenseCraft */
}

.nav-link {
  color: var(--secondary-color); /* Medium gray for inactive links */
  text-decoration: none;
  padding: 0.85rem 1.3rem; /* Adjusted padding for larger font */
  margin: 0 0.5rem;
  border-radius: var(--border-radius);
  transition: color 0.2s ease, border-bottom-color 0.2s ease;
  font-weight: 600; /* Bolder font weight */
  font-size: 1.05rem; /* Further increased font size */
  border-bottom: 3px solid transparent; /* Increased border thickness slightly */
}

.nav-link:hover {
  color: var(--primary-color); /* Green on hover */
}

.nav-link.router-link-exact-active {
  color: var(--primary-color); /* Green text for active tab */
  border-bottom-color: var(--primary-color); /* Green underline for active tab */
  /* font-weight: 700; */ /* Active link is already 600, ensure it stands out or keep same */
}

/* The <router-view /> itself doesn't need styling unless it's wrapped */
/* Content inside router-view should have its own padding via .page-container or similar */
</style>
