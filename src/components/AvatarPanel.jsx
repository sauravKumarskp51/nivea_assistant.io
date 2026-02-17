export default function AvatarPanel({ state = "idle" }) {
  return (
    <div className={`glass avatar ${state}`}>
      <div className="avatar-ring" />
      <img src="/avatar.png" alt="Nivya" />
      <h2>N I V Y A</h2>
      <p className="avatar-state">{state.toUpperCase()}</p>
    </div>
  );
}
