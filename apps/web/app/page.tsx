import { HealthPanel } from "../components/health-panel";
import styles from "./page.module.css";

const plannedCapabilities = [
  "LLM gateway",
  "API key auth",
  "Prompt versions",
  "Model routing",
  "Usage tracking",
  "Cost visibility",
  "Latency monitoring",
  "Failure tracking"
];

export default function Home() {
  return (
    <main className={styles.shell}>
      <section className={styles.hero}>
        <div className={styles.intro}>
          <p className={styles.eyebrow}>Local development foundation</p>
          <h1>Production AI Platform</h1>
          <p className={styles.lede}>
            A lightweight LLMOps gateway and dashboard built to prove the
            infrastructure around production AI workloads.
          </p>
        </div>
        <HealthPanel />
      </section>

      <section className={styles.grid} aria-label="Planned platform capabilities">
        {plannedCapabilities.map((capability) => (
          <article className={styles.card} key={capability}>
            <span className={styles.cardMarker} />
            <h2>{capability}</h2>
          </article>
        ))}
      </section>
    </main>
  );
}
