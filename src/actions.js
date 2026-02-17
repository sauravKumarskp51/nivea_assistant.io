export const actions = {
  music: {
    toggle: () =>
      fetch("http://127.0.0.1:5000/api/spotify/control", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "playpause" })
      })
  },

  alarm: {
    open: () =>
      fetch("http://127.0.0.1:5000/api/system/open-alarm")
  },

  calendar: {
    open: () =>
      window.open("https://calendar.google.com", "_blank")
  },

  files: {
    open: () =>
      fetch("http://127.0.0.1:5000/api/system/open-files")
  },

  browser: {
    open: () =>
      fetch("http://127.0.0.1:5000/api/system/open-browser")
  },

  settings: {
    open: () =>
      fetch("http://127.0.0.1:5000/api/system/open-settings")
  },

  /* 🌤️ WEATHER */
  weather: {
    check: () =>
      fetch("http://127.0.0.1:5000/api/system/open-weather")
  },

  /* 🔆 BRIGHTNESS */
    brightness: {
    increase: () =>
      fetch("http://127.0.0.1:5000/api/system/brightness", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "up" })
      }),

    decrease: () =>
      fetch("http://127.0.0.1:5000/api/system/brightness", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "down" })
      }),

      set: (value) =>
      fetch("http://127.0.0.1:5000/api/system/brightness", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "set", value })
      })
  },



  /* 🌗 THEME (FRONTEND SYNC) */
  theme: {
    dark: () =>
      fetch("http://127.0.0.1:5000/api/system/theme", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ theme: "dark" })
      }),

    light: () =>
      fetch("http://127.0.0.1:5000/api/system/theme", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ theme: "light" })
      })}



};
