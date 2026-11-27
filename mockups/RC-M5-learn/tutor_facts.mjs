// Facts for the tutor: each lab at its starting state, from the same labs.js the page runs.
// usage: node tutor_facts.mjs data
import { mkdirSync, writeFileSync } from "node:fs";
import { LABS } from "./labs.js";

const dir = process.argv[2] ?? "data";
mkdirSync(dir, { recursive: true });
const out = {};
for (const lab of LABS) {
  const facts = lab.facts(lab.start);
  const actions = Object.fromEntries(Object.entries(lab.actions).map(([k, a]) => [k, { kind: a.kind, text: a.text }]));
  out[lab.id] = { term: lab.term, state: lab.start, facts, actions, rule: lab.tutor(facts) };
}
writeFileSync(`${dir}/tutor_facts.json`, JSON.stringify(out, null, 1));
for (const [id, l] of Object.entries(out)) console.log(id, JSON.stringify(l.facts), "\n  rule:", l.rule.see, "->", l.rule.act);
