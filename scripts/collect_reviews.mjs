import crypto from "node:crypto";
import fs from "node:fs";
import readline from "node:readline";
import gplay from "google-play-scraper";

function parseArgs(argv) {
  const args = {
    ranking: "data/ranking_2026-06-25.csv",
    output: "data/reviews_2026-06-25.jsonl",
    reviewsPerGame: 200,
    throttle: 2,
  };
  for (let index = 2; index < argv.length; index += 1) {
    const key = argv[index];
    const value = argv[index + 1];
    if (key === "--ranking") args.ranking = value;
    if (key === "--output") args.output = value;
    if (key === "--reviews-per-game") args.reviewsPerGame = Number(value);
    if (key === "--throttle") args.throttle = Number(value);
    index += 1;
  }
  return args;
}

function parseCsvLine(line) {
  const fields = [];
  let field = "";
  let quoted = false;
  for (let index = 0; index < line.length; index += 1) {
    const char = line[index];
    if (char === '"' && quoted && line[index + 1] === '"') {
      field += '"';
      index += 1;
    } else if (char === '"') {
      quoted = !quoted;
    } else if (char === "," && !quoted) {
      fields.push(field);
      field = "";
    } else {
      field += char;
    }
  }
  fields.push(field);
  return fields;
}

function loadRanking(path) {
  const lines = fs.readFileSync(path, "utf8").replace(/^\uFEFF/, "").trim().split(/\r?\n/);
  return lines.slice(1).map((line) => {
    const [rank, appId, title] = parseCsvLine(line);
    return { rank: Number(rank), appId, title };
  });
}

function publicProfileToken(imageUrl) {
  if (!imageUrl) return null;
  try {
    const path = new URL(imageUrl).pathname;
    const segments = path.split("/").filter(Boolean);
    const marker = segments.find((part) => part.startsWith("ACg8oc") || part.startsWith("ALV-"));
    return marker ?? segments.slice(0, 3).join("/");
  } catch {
    return imageUrl;
  }
}

function reviewerIdentity(review) {
  const token = publicProfileToken(review.userImage);
  if (token) {
    return {
      reviewerKey: crypto.createHash("sha256").update(`profile:${token}`).digest("hex"),
      identityMethod: "public_profile_token_hash",
    };
  }
  return {
    reviewerKey: crypto.createHash("sha256").update(`review:${review.id}`).digest("hex"),
    identityMethod: "review_scoped_fallback",
  };
}

const args = parseArgs(process.argv);
const games = loadRanking(args.ranking);
fs.mkdirSync(new URL("../data/", import.meta.url), { recursive: true });
const output = fs.createWriteStream(args.output, { encoding: "utf8" });
let total = 0;

for (const game of games) {
  try {
    const result = await gplay.reviews({
      appId: game.appId,
      lang: "ko",
      country: "kr",
      sort: gplay.sort.NEWEST,
      num: args.reviewsPerGame,
      throttle: args.throttle,
    });
    for (const review of result.data) {
      const identity = reviewerIdentity(review);
      output.write(`${JSON.stringify({
        collectedAt: new Date().toISOString(),
        rank: game.rank,
        appId: game.appId,
        gameTitle: game.title,
        reviewId: review.id,
        reviewerKey: identity.reviewerKey,
        identityMethod: identity.identityMethod,
        userName: review.userName ?? null,
        userImage: review.userImage ?? null,
        score: review.score ?? null,
        reviewText: review.text ?? null,
        reviewDate: review.date ?? null,
        thumbsUp: review.thumbsUp ?? 0,
        appVersion: review.version ?? null,
        replyText: review.replyText ?? null,
        replyDate: review.replyDate ?? null,
        reviewUrl: review.url ?? null,
      })}\n`);
      total += 1;
    }
    console.log(`[${game.rank}/100] ${game.title}: ${result.data.length} reviews`);
  } catch (error) {
    console.error(`[${game.rank}/100] ${game.title}: ${error.message}`);
  }
}

await new Promise((resolve, reject) => {
  output.end(resolve);
  output.on("error", reject);
});
console.log(`Saved ${total} reviews to ${args.output}`);
