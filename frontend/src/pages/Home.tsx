import { Link } from "react-router-dom";
import {
  ArrowRight,
  ArrowUpRight,
  FileText,
  ScanLine,
  Check,
} from "lucide-react";
import { motion, useReducedMotion } from "framer-motion";
import { EviRobot } from "../components/evi/Evi";
export default function Home() {
  const reduced = useReducedMotion();
  return (
    <div className="home">
      <header className="home-nav">
        <Link className="brand" to="/">
          <span className="brand-mark">e.</span>Evidentia
          <span className="brand-dot">®</span>
        </Link>
        <span className="home-caption">ENTERPRISE KNOWLEDGE INTELLIGENCE</span>
        <Link to="/ask" className="button ghost">
          Open workspace <ArrowUpRight size={16} />
        </Link>
      </header>
      <main className="hero">
        <motion.div
          initial={reduced ? false : { opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="hero-copy"
        >
          <span className="eyebrow">
            <span className="little-star">✳</span> KNOWLEDGE, WITH A PAPER
            TRAIL.
          </span>
          <h1>
            Every answer
            <br />
            deserves <em>evidence.</em>
          </h1>
          <p>
            Turn your documents into knowledge you can question, inspect and
            verify.
          </p>
          <div className="hero-actions">
            <Link to="/ask" className="button primary">
              Enter Evidentia <ArrowRight size={18} />
            </Link>
            <a className="text-link" href="#how">
              Follow the evidence <span>↘</span>
            </a>
          </div>
          <div className="hero-footnote">
            <span className="hairline" /> A little curiosity. A lot of clarity.
          </div>
        </motion.div>
        <div
          className="hero-art"
          aria-label="Illustration of documents connected to evidence and an answer"
        >
          <div className="orbital orbital-one" />
          <div className="orbital orbital-two" />
          <svg
            className="hero-threads"
            viewBox="0 0 550 500"
            aria-hidden="true"
          >
            <path d="M100 110C280 90 180 360 400 350M120 400C330 420 290 110 425 150" />
          </svg>
          <div className="concept-card concept-doc">
            <FileText />
            <span>01 / KNOWLEDGE</span>
            <strong>The starting point.</strong>
            <div className="illustration-lines">
              <i />
              <i />
              <i />
            </div>
          </div>
          <div className="hero-evi">
            <EviRobot state="greeting" large />
            <span>Meet Evi. Curious by design.</span>
          </div>
          <div className="concept-card concept-proof">
            <span className="proof-icon">
              <Check size={17} />
            </span>
            <span>02 / EVIDENCE</span>
            <strong>Something to stand on.</strong>
            <p>Traceable. Inspectable. Yours.</p>
          </div>
          <span className="art-note">An illustration of the process</span>
        </div>
      </main>
      <section className="home-how" id="how">
        <div>
          <span className="eyebrow">FROM INFORMATION TO UNDERSTANDING</span>
          <h2>Nothing without a thread.</h2>
        </div>
        <div className="how-grid">
          {[
            [
              FileText,
              "Bring your knowledge",
              "Upload the documents you want to investigate.",
            ],
            [
              ScanLine,
              "Look beneath the answer",
              "Follow citations, retrieval decisions and validation.",
            ],
            [
              Check,
              "Put it to the test",
              "Evaluate retrieval and answer quality against your own data.",
            ],
          ].map(([Icon, title, description], i) => {
            const I = Icon as typeof FileText;
            return (
              <article key={String(title)}>
                <span className="step-number">0{i + 1}</span>
                <I size={22} />
                <h3>{String(title)}</h3>
                <p>{String(description)}</p>
              </article>
            );
          })}
        </div>
      </section>
      <footer className="home-footer">
        <span>Evidentia / Enterprise Knowledge Intelligence</span>
        <span>Built around one thing: evidence.</span>
      </footer>
    </div>
  );
}
