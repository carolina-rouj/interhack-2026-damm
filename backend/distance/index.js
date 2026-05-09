#!/usr/bin/env node

import 'dotenv/config';

const API_KEY = process.env.GOOGLE_MAPS_API_KEY;

const DIST_WEIGHT = 0.5;
const TIME_WEIGHT = 0.5;

function die(msg) {
  console.error(`Error: ${msg}`);
  process.exit(1);
}

async function getDrivingInfo(latA, lngA, destinations) {
  const origins = `${latA},${lngA}`;
  const dests = destinations.map(d => `${d.lat},${d.lng}`).join('|');
  const url =
    `https://maps.googleapis.com/maps/api/distancematrix/json` +
    `?origins=${encodeURIComponent(origins)}` +
    `&destinations=${encodeURIComponent(dests)}` +
    `&mode=driving` +
    `&departure_time=now` +
    `&key=${API_KEY}`;

  let res;
  try {
    res = await fetch(url);
  } catch (err) {
    die(`Network error: ${err.message}`);
  }

  if (!res.ok) die(`API request failed with HTTP ${res.status}`);

  const data = await res.json();

  if (data.status !== 'OK') die(`API error: ${data.status} — ${data.error_message ?? ''}`);

  const elements = data.rows?.[0]?.elements;
  if (!elements) die('Unexpected API response structure');

  return elements.map((element, i) => {
    if (element.status !== 'OK') return { index: i, error: element.status };
    return {
      index: i,
      distanceMeters: element.distance.value,
      // duration_in_traffic is present when departure_time=now is accepted
      durationSeconds: element.duration_in_traffic?.value ?? element.duration.value,
      trafficAware: !!element.duration_in_traffic,
    };
  });
}

// Cost 1–10 proportional to how bad the route is relative to the best/worst in the batch.
// A destination twice as costly as the best gets a score that reflects that gap directly.
function assignCosts(results) {
  const valid = results.filter(r => !r.error);
  if (valid.length === 0) return results;

  const minDist = Math.min(...valid.map(r => r.distanceMeters));
  const maxDist = Math.max(...valid.map(r => r.distanceMeters));
  const minDur  = Math.min(...valid.map(r => r.durationSeconds));
  const maxDur  = Math.max(...valid.map(r => r.durationSeconds));

  return results.map(r => {
    if (r.error) return r;
    const normDist = maxDist === minDist ? 0 : (r.distanceMeters - minDist) / (maxDist - minDist);
    const normDur  = maxDur  === minDur  ? 0 : (r.durationSeconds - minDur)  / (maxDur  - minDur);
    const cost = Math.round((DIST_WEIGHT * normDist + TIME_WEIGHT * normDur) * 9 + 1);
    return { ...r, cost };
  });
}

function formatDuration(seconds) {
  const totalMins = Math.round(seconds / 60);
  const hours = Math.floor(totalMins / 60);
  const mins = totalMins % 60;
  if (hours === 0) return `${mins} mins`;
  if (mins === 0) return `${hours} hour${hours !== 1 ? 's' : ''}`;
  return `${hours} hour${hours !== 1 ? 's' : ''} ${mins} mins`;
}

(async () => {
  if (!API_KEY) die('GOOGLE_MAPS_API_KEY environment variable is not set');

  const args = process.argv.slice(2);
  if (args.length < 4 || args.length % 2 !== 0) {
    console.error('Usage: node index.js <latA> <lngA> <latB> <lngB> [<latC> <lngC> ...]');
    console.error('Example: node index.js 41.3851 2.1734 40.4168 -3.7038 48.8566 2.3522');
    process.exit(1);
  }

  const [latA, lngA, ...rest] = args.map(parseFloat);

  if (latA < -90 || latA > 90) die('Origin latitude must be between -90 and 90');
  if (lngA < -180 || lngA > 180) die('Origin longitude must be between -180 and 180');

  const destinations = [];
  for (let i = 0; i < rest.length; i += 2) {
    const lat = rest[i], lng = rest[i + 1];
    if (isNaN(lat) || isNaN(lng)) die(`Invalid coordinates at destination ${destinations.length + 1}`);
    if (lat < -90 || lat > 90) die(`Destination ${destinations.length + 1} latitude out of range`);
    if (lng < -180 || lng > 180) die(`Destination ${destinations.length + 1} longitude out of range`);
    destinations.push({ lat, lng });
  }

  const raw = await getDrivingInfo(latA, lngA, destinations);
  const results = assignCosts(raw);

  const trafficNote = raw.find(r => r.trafficAware) ? '(traffic-aware)' : '(no traffic data)';
  console.log(`Origin: ${latA}, ${lngA} — durations ${trafficNote}\n`);

  for (const result of results) {
    const d = destinations[result.index];
    const label = `Destination ${result.index + 1} (${d.lat}, ${d.lng})`;
    if (result.error) {
      console.log(`${label}: Route error — ${result.error}`);
    } else {
      console.log(`${label}: ${result.distanceMeters} m | ${formatDuration(result.durationSeconds)} | cost ${result.cost}/10`);
    }
  }
})();
