import { createRouter, createWebHistory } from 'vue-router';
// import LiveMapView from '@/views/LiveMapView.vue'; // To be removed
import MasterConfigView from '@/views/MasterConfigView.vue'; // New Master Config
import LocalModeConfigView from '@/views/LocalModeConfigView.vue'; // Renamed from PersonalModeConfigView
import TrackerModeConfigView from '@/views/TrackerModeConfigView.vue'; // Import the new view
// import HomeView from '@/views/HomeView.vue';
// import ConfigurationView from '@/views/ConfigurationView.vue'; // Old, to be removed or reworked
import ConfigurationSuiteView from '@/views/ConfigurationSuiteView.vue'; // Import the main config view
// import LiveDataView from '@/views/LiveDataView.vue';
// import DeviceTrackingView from '@/views/DeviceTrackingView.vue';

const routes = [
  // {
  //   path: '/',
  //   name: 'LiveMap',
  //   component: LiveMapView, // Remove this route
  // },
  {
    path: '/', // Make TrackerMode the default landing page
    name: 'TrackerModeConfiguration', // Keep original name for consistency or change to TrackerModeDefault
    component: TrackerModeConfigView, 
  },
  {
    path: '/config-master',
    name: 'MasterConfiguration', // Changed from MasterConfigRedirect for clarity
    component: MasterConfigView, // Route for the new master config page
  },
  {
    path: '/config-local', // Renamed path
    name: 'LocalModeConfiguration', // Renamed name
    component: LocalModeConfigView, // Route for the new personal mode config page
  },
  {
    path: '/config-tracker', // Define path for tracker mode
    name: 'TrackerModeConfig', // This is the specific path for Tracker Mode if not default
    component: TrackerModeConfigView, // Use the new component
  },
  {
    path: '/config',
    name: 'Configuration',
    component: ConfigurationSuiteView, 
  },
  // {
  //   path: '/live-data',
  //   name: 'LiveData',
  //   component: LiveDataView,
  // },
  // {
  //   path: '/device-tracking',
  //   name: 'DeviceTracking',
  //   component: DeviceTrackingView,
  // },
  // {
  //   path: '/config', // Old path, decide if to keep, redirect, or remove
  //   name: 'Configuration',
  //   component: ConfigurationSuiteView, 
  // },
];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
});

export default router; 