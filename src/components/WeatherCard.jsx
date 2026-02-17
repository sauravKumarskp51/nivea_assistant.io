import { useEffect, useState } from "react";

const API_KEY = "d888c2ef950c26d142d75843687c98cf";

export default function WeatherCard() {
  const [weather, setWeather] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!navigator.geolocation) {
      setError(true);
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude } = position.coords;

        fetch(
          `https://api.openweathermap.org/data/2.5/weather?lat=${latitude}&lon=${longitude}&units=metric&appid=${API_KEY}`
        )
          .then(res => res.json())
          .then(data => setWeather(data))
          .catch(() => setError(true));
      },
      () => setError(true)
    );
  }, []);

  if (error) {
    return (
      <div className="glass weather-card">
        📍 Location access denied
      </div>
    );
  }

  if (!weather) {
    return (
      <div className="glass weather-card">
        Fetching local weather...
      </div>
    );
  }

  const temp = Math.round(weather.main.temp);
  const feels = Math.round(weather.main.feels_like);
  const condition = weather.weather[0].main;
  const sunrise = new Date(weather.sys.sunrise * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  const sunset = new Date(weather.sys.sunset * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });


  return (
    <div className="glass weather-card">

      {/* HEADER */}
      <div className="weather-header">
        <div>
          <h3>{new Date().toDateString()}</h3>
          <p className="time">{new Date().toLocaleTimeString([], {  hour: "2-digit",minute: "2-digit"})}</p>
        </div>

        <div className="weather-icon animate">
          {getWeatherIcon(condition)}
        </div>
      </div>

      {/* TEMP */}
      <div className="weather-temp">
        <span className="temp">{temp}°</span>
        <span className="unit">C</span>
      </div>

      <p className="condition">{condition}</p>
      <p className="feels">Feels like {feels}°C</p>

      {/* SUN */}
      <div className="sun-times">
        <span>🌅 {sunrise}</span>
        <span>🌇 {sunset}</span>
      </div>

      <p className="location">📍 {weather.name}</p>
    </div>
  );
}

function getWeatherIcon(condition) {
  switch (condition) {
    case "Clear": return "☀️";
    case "Clouds": return "☁️";
    case "Rain": return "🌧";
    case "Thunderstorm": return "⛈";
    case "Snow": return "❄️";
    default: return "🌥";
  }
}
