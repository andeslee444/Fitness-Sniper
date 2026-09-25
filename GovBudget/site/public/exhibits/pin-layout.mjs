// Keep projected 30px topic buttons separate, including when mesh bounds share a center.
export function layoutPins(points, width, height) {
  const placed = [];
  const clamp = (n, min, max) => Math.max(min, Math.min(max, n));
  return points.map(point => {
    if (point.hidden) return point;
    const origin = { x: clamp(point.x, 18, width - 18), y: clamp(point.y, 18, height - 54) };
    let position;
    for (let ring = 0; ring <= 8 && !position; ring++) {
      for (const [dx, dy] of [[1,0],[-1,0],[0,-1],[0,1],[1,-1],[-1,-1],[1,1],[-1,1]]) {
        const candidate = { x: origin.x + dx * ring * 38, y: origin.y + dy * ring * 38 };
        if (candidate.x < 18 || candidate.x > width - 18 || candidate.y < 18 || candidate.y > height - 54) continue;
        if (placed.every(p => Math.abs(candidate.x-p.x) >= 38 || Math.abs(candidate.y-p.y) >= 38)) {
          position = candidate; break;
        }
      }
    }
    if (!position) return { ...point, hidden: true };
    placed.push(position);
    return { ...point, ...position };
  });
}
