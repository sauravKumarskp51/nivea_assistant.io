import { actions } from "../actions";

export default function SkillPanel() {
  return (
    <div className="glass skill-panel">
      <div className="skill-grid">

        <Skill icon="⏰" label="Alarm" onClick={actions.alarm.open} />
        <Skill icon="📅" label="Calendar" onClick={actions.calendar.open} />
        <Skill icon="🌐" label="Browser" onClick={actions.browser.open} />
        <Skill icon="📂" label="Files" onClick={actions.files.open} />
        <Skill icon="⚙" label="Settings" onClick={actions.settings.open} />
        <Skill icon="🌤️" label="Weather" onClick={actions.weather.check}/>
        <Skill icon="🔆" label="Brightness +" onClick={actions.brightness.increase} />
        <Skill icon="🔅" label="Brightness -" onClick={actions.brightness.decrease} />


      </div>
    </div>
  );
}

function Skill({ icon, label, onClick }) {
  return (
    <button
      className="skill-tile"
      onClick={onClick}
      type="button"
    >
      <span className="icon">{icon}</span>
      <span className="label">{label}</span>
    </button>
  );
}

