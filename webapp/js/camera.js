
const { createApp } = Vue;

createApp({
  data() {
    return {
      activeNav: "Cameras",
      selectedId: "CAM-01",
      detectionEnabled: true,

      currentDate: "",
      currentTime: "",

      navigation: [
        { label: "Cameras", icon: "▣" },
        { label: "Overview", icon: "⌂" },
        { label: "Events", icon: "⚑" },
        { label: "Evidence", icon: "◇" },
        { label: "Support", icon: "ⓘ" },
        { label: "System Settings", icon: "⚙" }
      ],

      cameras: [
        {
          id: "CAM-01",
          name: "Main Entrance",
          status: "Live",
          detected: true,
          detection: "Knife detected"
        },
        {
          id: "CAM-02",
          name: "North Corridor",
          status: "Live",
          detected: false,
          detection: ""
        },
        {
          id: "CAM-03",
          name: "Parking Area",
          status: "Live",
          detected: false,
          detection: ""
        },
        {
          id: "CAM-04",
          name: "Rear Entrance",
          status: "Live",
          detected: false,
          detection: ""
        },
        {
          id: "CAM-05",
          name: "Main Hall",
          status: "Live",
          detected: false,
          detection: ""
        },
        {
          id: "CAM-06",
          name: "Side Gate",
          status: "Live",
          detected: false,
          detection: ""
        },
        {
          id: "CAM-07",
          name: "East Wing",
          status: "Live",
          detected: false,
          detection: ""
        }
      ]
    };
  },

  computed: {
    selectedCamera() {
      return this.cameras.find(
        camera => camera.id === this.selectedId
      ) || this.cameras[0];
    }
  },

  methods: {
    updateClock() {
      const now = new Date();

      this.currentDate = new Intl.DateTimeFormat("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric"
      }).format(now);

      this.currentTime = new Intl.DateTimeFormat("en-GB", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false
      }).format(now);
    },

    selectCamera(camera) {
      this.selectedId = camera.id;
    },

    previousCamera() {
      const currentIndex = this.cameras.findIndex(
        camera => camera.id === this.selectedId
      );

      const previousIndex =
        (currentIndex - 1 + this.cameras.length) %
        this.cameras.length;

      this.selectedId = this.cameras[previousIndex].id;
    },

    navigate(item) {
      this.activeNav = item.label;

      if (item.label === "Cameras") {
        return;
      }

      // These sections will be implemented as separate pages.
      alert(item.label + " page will be implemented next.");
    },

    logout() {
      window.location.href = "index.html";
    }
  },

  mounted() {
    this.updateClock();

    this.clockInterval = window.setInterval(
      this.updateClock,
      1000
    );
  },

  beforeUnmount() {
    window.clearInterval(this.clockInterval);
  }
}).mount("#cameraApp");
