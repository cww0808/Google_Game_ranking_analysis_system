import fs from "node:fs";
import gplay from "google-play-scraper";

const output = process.argv[2] ?? "data/ranking.csv";
const apps = await gplay.list({
  category: gplay.category.GAME,
  collection: gplay.collection.TOP_FREE,
  num: 100,
  country: "kr",
  lang: "ko",
});

if (apps.length !== 100) {
  throw new Error(`Expected 100 chart entries, received ${apps.length}`);
}

const quote = (value) => `"${String(value ?? "").replaceAll('"', '""')}"`;
const rows = [
  "rank,app_id,title",
  ...apps.map((app, index) => [index + 1, app.appId, quote(app.title)].join(",")),
];
fs.mkdirSync(new URL("../data/", import.meta.url), { recursive: true });
fs.writeFileSync(output, `${rows.join("\n")}\n`, "utf8");
console.log(`Saved ${apps.length} ranked package IDs to ${output}`);
