"use client";

type PlanetType = "earth" | "mars" | "moon";

export default function PlanetSelector({ activePlanet, onChange }: { activePlanet: PlanetType; onChange: (planet: PlanetType) => void; }) {
  const planets = [{ id: "earth", label: "Earth", icon: "🌍" }, { id: "mars", label: "Mars", icon: "🔴" }, { id: "moon", label: "Moon", icon: "🌕" }] as const;
  return <div className="planet-selector">{planets.map((planet) => <button key={planet.id} type="button" onClick={() => onChange(planet.id)} className={activePlanet === planet.id ? "planet-button active" : "planet-button"}><span>{planet.icon}</span>{planet.label}</button>)}</div>;
}
